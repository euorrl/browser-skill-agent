"""文件输入控件上传与下载保存。"""

from pathlib import Path


class Files:
    def __init__(self, session):
        self.s = session

    def upload(self, target, paths):
        paths = [paths] if isinstance(paths, str) else paths
        files = [str(Path(path).resolve(strict=True)) for path in paths]
        self.s.target(target).set_input_files(files)
        return {"selected_files": [Path(path).name for path in files]}

    def download(self, target, filename=None):
        directory = Path.cwd() / "data" / "downloads"
        directory.mkdir(parents=True, exist_ok=True)
        with self.s.current().expect_download(timeout=30_000) as pending:
            self.s.target(target).click()
        download = pending.value
        name = filename or download.suggested_filename
        if not name or Path(name).name != name or name in (".", ".."):
            raise ValueError("filename 必须为文件名，不能包含路径")
        path = directory / name
        # 自动避开同名文件，不覆盖用户已有下载。
        number = 1
        while path.exists():
            path = directory / f"{Path(name).stem}-{number}{Path(name).suffix}"
            number += 1
        download.save_as(path)
        error = download.failure()
        if error:
            raise RuntimeError(error)
        return {"path": str(path), "bytes": path.stat().st_size}
