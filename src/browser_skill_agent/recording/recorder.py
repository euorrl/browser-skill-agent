"""可见浏览器录制与本地控制页；所有事件留在本机。"""
import argparse
import asyncio
import hashlib
from pathlib import Path
import re
from urllib.parse import urlsplit

from playwright.async_api import async_playwright
from .storage import Recording, clean_url, now

ASSETS = Path(__file__).parent


class Recorder:
    def __init__(self, context, root):
        self.context = context
        self.root = Path(root).resolve()
        self.current = None
        self.control = None
        self.start_url = ""
        self.pages = {}
        self.frames = {}
        self.owners = {}
        self.tasks = set()
        self.downloads = {}
        self.lock = asyncio.Lock()
        self.closed = asyncio.Event()
        self.last_error = None

    def spawn(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        def done(t):
            self.tasks.discard(t)
            if not t.cancelled() and t.exception():
                self.last_error = f"录制异常：{type(t.exception()).__name__}"
                if self.current:
                    self.current.event("recorder_error", message=self.last_error)
                    self.current.save()
        task.add_done_callback(done)
        return task

    async def open(self, url=""):
        await self.context.expose_binding("__bsaRecorderReady", self.ready)
        await self.context.expose_binding("__bsaRecord", self.capture)
        await self.context.add_init_script(path=str(ASSETS / "browser.js"))
        self.context.on("page", self.discover)
        self.context.on("close", lambda *_: self.closed.set())
        self.control = await self.context.new_page()
        await self.control.expose_binding("__bsaControl", self.command)
        self.control.on("close", lambda *_: self.closed.set())
        await self.control.goto((ASSETS / "control.html").as_uri())
        await self.control.locator("#url").fill(url)
        await self.control.bring_to_front()
        for tab in list(self.context.pages):
            if tab!=self.control and tab.url=='about:blank':await tab.close()
        return self.control

    def discover(self, page):
        # 新页面可能尚无 URL，等首次导航或注入脚本握手后再识别。
        page.once("framenavigated", lambda _: self.track(page))
        self.track(page)

    def track(self, page):
        # Edge 下载中心是浏览器内部页面，不是用户任务标签页，不能逐页关闭。
        if not page.url or urlsplit(page.url).scheme in ('edge','chrome','devtools','chrome-extension'):
            return
        if page == self.control or page in self.pages or not self.current or self.current.session["status"] != "recording":
            return
        rec = self.current
        pid = f"p{len(rec.session['pages'])+1}"
        self.pages[page] = pid
        self.owners[page] = rec
        rec.session["pages"][pid] = {"url":clean_url(page.url),"title":"","closed":False}
        self.frame_id(page,page.main_frame)
        rec.event("page_open", pid, url=clean_url(page.url))
        page.on("framenavigated", lambda frame: self.navigated(page, frame))
        page.on("close", lambda: self.page_closed(page))
        page.on("download", lambda download: self.download_started(page, download))
        page.on("dialog", lambda dialog: self.spawn(self.handle_dialog(page, dialog)))
        page.on("crash", lambda: rec.event("page_crashed", pid))
        self.spawn(self.opener(page, rec, pid))
        rec.save()

    async def opener(self, page, rec, pid):
        parent = await page.opener()
        if parent in self.pages:
            rec.session["pages"][pid]["opener_page_id"] = self.pages[parent]
            rec.save()

    def frame_id(self, page, frame):
        key = (page, frame)
        if key not in self.frames:
            self.frames[key] = f"f{sum(p == page for p,f in self.frames)+1}"
        rec=self.owners.get(page)
        if rec:
            rec.session['pages'][self.pages[page]].setdefault('frames',{})[self.frames[key]]={
                'url':clean_url(frame.url),'name':frame.name,'main':frame==page.main_frame,
                'parent_frame_id':self.frame_id(page,frame.parent_frame) if frame.parent_frame else None}
        return self.frames[key]

    async def ready(self, source):
        page = source["page"]
        self.track(page)
        rec = self.owners.get(page)
        if rec and rec == self.current and rec.session["status"] == "recording":
            return {"id":rec.id}
        return None

    async def capture(self, source, payload):
        page, frame = source["page"], source["frame"]
        rec = self.owners.get(page)
        if not rec or rec != self.current or rec.session["status"] not in ("recording","finishing"):
            return
        if not isinstance(payload, dict) or payload.get("recording_id") != rec.id:
            return
        kind = payload.get("type")
        if kind not in {"input","click","double_click","select","set_checked","press","upload","scroll","observation",
                        "file_hash","page_active","navigation_observed","document_ready"}:
            return
        # 只接受已知事件字段，不让网页通过载荷指定输出路径或会话状态。
        allowed = {"event_id","document_id","client_time","url","title","element_key","target","before",
                   "controls","controls_truncated","value","value_truncated","redacted","options","checked","key","files","related_event","text","truncated","x","y"}
        data = {k:v for k,v in payload.items() if k in allowed}
        data["url"] = clean_url(str(data.get("url", frame.url)))
        if isinstance(data.get("before"), dict):
            data["before"]["url"] = clean_url(str(data["before"].get("url", "")))
        if data.get("redacted") or data.get("target", {}).get("sensitive"):
            data["value"] = None
            data["redacted"] = True
        pid = self.pages[page]
        event = rec.event(kind, pid, self.frame_id(page, frame), frame_url=clean_url(frame.url), **data)
        rec.action(event)
        if frame == page.main_frame:
            rec.session["pages"][pid].update(url=data["url"],title=data.get("title", ""))
        rec.save()

    def navigated(self, page, frame):
        rec = self.owners.get(page)
        if rec and rec.session["status"] == "recording":
            rec.event("navigation",self.pages[page],self.frame_id(page,frame),url=clean_url(frame.url),main_frame=frame==page.main_frame)
            rec.save()

    def page_closed(self, page):
        rec = self.owners.get(page)
        if rec:
            rec.session["pages"][self.pages[page]]["closed"] = True
            if rec.session["status"] == "recording":
                rec.event("page_close", self.pages[page])
            rec.save()

    async def handle_dialog(self, page, dialog):
        # 不安装处理器会自动取消原生弹窗；这里交由用户在控制页选择。
        rec = self.owners.get(page)
        if not rec or rec.session["status"] != "recording":
            await dialog.dismiss()
            return
        self.pending_dialog = (page, dialog, rec)
        await self.control.bring_to_front()

    def download_started(self, page, download):
        rec = self.owners.get(page)
        if not rec or rec.session["status"] not in ("recording","finishing"):
            return
        item = {"id":f"d{len(rec.session['downloads'])+1}","page_id":self.pages[page],
                "suggested_filename":download.suggested_filename,"url":clean_url(download.url),
                "status":"downloading","started_at":now()}
        rec.session["downloads"].append(item)
        rec.event("download_started",self.pages[page],download_id=item["id"],suggested_filename=item["suggested_filename"],url=item["url"])
        rec.save()
        task = self.spawn(self.save_download(rec, download, item))
        self.downloads[download] = (rec, task)

    async def save_download(self, rec, download, item):
        try:
            rec.download_dir.mkdir(parents=True, exist_ok=True)
            name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', download.suggested_filename).strip(' .')[:160] or 'download'
            # 独立编号前缀同时避免重名和 Windows 保留文件名。
            path = rec.download_dir / (item['id']+'-'+name)
            await download.save_as(str(path))
            def digest():
                result = hashlib.sha256()
                with path.open('rb') as stream:
                    for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
                return result.hexdigest()
            item.update(status='completed',path=str(path),size=path.stat().st_size,sha256=await asyncio.to_thread(digest))
        except asyncio.CancelledError:
            item.update(status='cancelled',error='录制关闭，下载未完成')
        except Exception as exc:
            item.update(status='cancelled' if rec.session['status']=='abandoned' else 'failed',error=type(exc).__name__)
        finally:
            item['ended_at'] = now()
            rec.event('download_'+item['status'],item['page_id'],download_id=item['id'],details=dict(item))
            rec.save()

    async def flush(self, rec, freeze=False):
        for page, owner in list(self.owners.items()):
            if owner != rec or page.is_closed():continue
            for frame in page.frames:
                try:
                    await asyncio.wait_for(frame.evaluate("async freeze => {if(window.__bsaRecorderFlush) await window.__bsaRecorderFlush(freeze);}",freeze),3)
                except Exception:
                    rec.event('flush_unavailable',self.pages[page],self.frame_id(page,frame),url=clean_url(frame.url))

    async def begin(self, url):
        parts = urlsplit(url)
        if parts.scheme not in ('http','https','file') or (parts.scheme in ('http','https') and not parts.netloc):
            raise ValueError('请输入完整的 http:// 或 https:// 网址；本地演示可使用 file:// 地址。')
        if self.current and self.current.session['status'] in ('recording','finishing'):
            raise ValueError('当前正在录制，请先结束或重新开始。')
        if self.current:
            for old_page, owner in list(self.owners.items()):
                if owner==self.current and not old_page.is_closed():
                    await old_page.close()
        self.start_url = url
        self.current = Recording(self.root,url)
        page = await self.context.new_page()
        self.track(page)
        try:
            await page.goto(url,wait_until='domcontentloaded',timeout=30000)
        except Exception as exc:
            self.current.event('navigation_error',self.pages[page],error=type(exc).__name__,url=clean_url(url))
            self.current.session['notes'].append('入口加载未正常完成；可以在浏览器继续操作，也可重新开始。')
            self.current.save()
        await page.bring_to_front()

    async def finish(self, rec):
        await self.flush(rec,freeze=True)
        await asyncio.sleep(.3)
        while rec.session['status']=='finishing':
            pending=[t for r,t in self.downloads.values() if r==rec and not t.done()]
            if not pending:break
            await asyncio.gather(*pending,return_exceptions=True)
        if rec.session['status']=='finishing':
            rec.session.update(status='completed',ended_at=now())
            rec.event('recording_finished')
            rec.save()

    async def restart(self):
        old=self.current
        if not old:raise ValueError('请先开始录制。')
        await self.flush(old,freeze=True)
        old.session.update(status='abandoned',ended_at=now())
        old.event('recording_abandoned',reason='用户重新开始；网站已发生的操作没有撤销')
        old.save()
        # 工作台录制没有控制标签页，保留临时空页避免关闭最后一页退出整个浏览器。
        guard = await self.context.new_page() if self.control is None else None
        if getattr(self,'pending_dialog',None):
            await self.pending_dialog[1].dismiss()
            self.pending_dialog=None
        for download,(rec,task) in list(self.downloads.items()):
            if rec==old and not task.done():
                await download.cancel()
        for page,rec in list(self.owners.items()):
            if rec==old and not page.is_closed():await page.close()
        await self.begin(self.start_url)
        if guard is not None:
            await guard.close()

    def status(self):
        rec=self.current
        result={'state':rec.session['status'] if rec else 'idle','error':self.last_error}
        if rec:
            result.update(id=rec.id,action_count=len(rec.actions),page_count=len(rec.session['pages']),
                          uploads=sum(a['kind']=='upload' for a in rec.actions),
                          downloads=rec.session['downloads'],folder=str(rec.folder),
                          actions=[{'kind':a['kind'],'name':a.get('target',{}).get('name') or a.get('target',{}).get('id') or a.get('target',{}).get('tag','')} for a in rec.actions[-30:]])
        dialog=getattr(self,'pending_dialog',None)
        if dialog:result['dialog']={'type':dialog[1].type,'message':dialog[1].message}
        return result

    async def command(self, source, command, value=None):
        if source['page']!=self.control or source['frame']!=self.control.main_frame or self.control.url!=(ASSETS/'control.html').as_uri():
            return {'error':'仅本地录制控制页可操作录制状态'}
        if command=='status':return self.status()
        async with self.lock:
            self.last_error=None
            try:
                if command=='start':await self.begin(str(value or '').strip())
                elif command=='restart':await self.restart()
                elif command=='stop':
                    if getattr(self,'pending_dialog',None):raise ValueError('请先处理网页弹窗，再结束录制。')
                    if self.current and self.current.session['status']=='recording':
                        self.current.session['status']='finishing';self.current.save();self.spawn(self.finish(self.current))
                elif command=='dialog' and getattr(self,'pending_dialog',None):
                    page,dialog,rec=self.pending_dialog
                    accepted=bool(value and value.get('accept'))
                    event=rec.event('dialog',self.pages[page],dialog_type=dialog.type,message=dialog.message,accepted=accepted)
                    rec.action(event)
                    # prompt 文本不写入记录，避免把敏感输入沉淀进去。
                    if accepted:await dialog.accept(str((value or {}).get('text','')))
                    else:await dialog.dismiss()
                    self.pending_dialog=None;rec.save();await page.bring_to_front()
                elif command not in ('stop','dialog'):raise ValueError('未知录制命令')
            except Exception as exc:
                self.last_error=str(exc) if isinstance(exc,ValueError) else f'操作未完成：{type(exc).__name__}'
            return self.status()

    async def shutdown(self):
        if self.current and self.current.session['status'] in ('recording','finishing'):
            self.current.session.update(status='interrupted',ended_at=now())
            self.current.event('recording_interrupted',reason='控制页或浏览器关闭，或终端中断')
            self.current.save()
        for task in list(self.tasks):task.cancel()
        if self.tasks:await asyncio.gather(*list(self.tasks),return_exceptions=True)


async def serve(args):
    async with async_playwright() as pw:
        context=await pw.chromium.launch_persistent_context(
            str(args.profile_dir.resolve()) if args.profile_dir else '',channel='msedge',headless=False,
            accept_downloads=True,ignore_https_errors=args.ignore_https_errors)
        recorder=Recorder(context,Path.cwd())
        try:
            await recorder.open(args.url)
            print('录制控制页已打开。请尽量完整、连贯地演示；正常等待网页加载，无需加快操作。',flush=True)
            print('结束后记录自动保存；关闭控制页将退出录制浏览器。',flush=True)
            await recorder.closed.wait()
        finally:
            await recorder.shutdown()
            await context.close()


def main(argv=None):
    parser=argparse.ArgumentParser(description='录制用户手动浏览器操作，不调用 LLM')
    parser.add_argument('--url',default='',help='预填起始网址，也可在控制页输入')
    parser.add_argument('--profile-dir',type=Path,help='可选：复用登录会话目录，不可与其他浏览器同时占用')
    parser.add_argument('--ignore-https-errors',action='store_true',help='仅信任目标网站时忽略证书错误')
    args=parser.parse_args(argv)
    try:asyncio.run(serve(args))
    except KeyboardInterrupt:print('录制已中断，已有记录保留。')
    except Exception as exc:
        print(f'录制器启动或运行失败：{type(exc).__name__}: {exc}')
        return 1
    return 0
