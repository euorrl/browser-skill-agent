"""文件输入控件上传与下载保存。"""

from pathlib import Path, PureWindowsPath

from ..output import progress


def validate_filename(name):
    if (not isinstance(name, str) or not name or name in (".", "..")
            or any(c in name for c in '<>:"/\\|?*') or any(ord(c) < 32 for c in name)
            or name.endswith((".", " ")) or PureWindowsPath(name).is_reserved()):
        raise ValueError("下载名称必须是普通文件名，不能包含路径或保留字符")
    return name


class FileOptions:
    """本次运行明确选择的文件和保存目录，不扫描上传目录。"""

    def __init__(self, upload_dir="files/uploads", upload_files=(),
                 download_dir="files/downloads", download_name=None):
        self.upload_dir = Path(upload_dir).resolve()
        self.download_dir = Path(download_dir).resolve()
        self.download_name = validate_filename(download_name) if download_name is not None else None
        self.uploads = {}
        for value in upload_files:
            path = Path(value)
            path = (path if path.is_absolute() else self.upload_dir / path).resolve(strict=True)
            if not path.is_file():
                raise ValueError(f"上传对象不是文件：{path}")
            if path not in self.uploads.values():
                self.uploads[f"u{len(self.uploads) + 1}"] = path
        if self.download_dir.exists() and not self.download_dir.is_dir():
            raise ValueError(f"下载目录不是文件夹：{self.download_dir}")

    @classmethod
    def from_skill(cls, skill):
        """只解析 Skill 明确声明的文件参数，不将普通参数当作文件路径。"""
        mapping = skill.get("file_params", {})
        allowed = {"uploads", "upload_dir", "download_dir", "download_name"}
        if not isinstance(mapping, dict) or set(mapping) - allowed:
            raise ValueError("file_params 仅支持 uploads、upload_dir、download_dir、download_name")
        params = skill.get("params", {})

        def parameter(name):
            if not isinstance(name, str) or not name.strip():
                raise ValueError("file_params 的值必须是参数名，而不是模板或路径")
            value = params.get(name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"文件参数不能为空：{name}")
            return value

        names = mapping.get("uploads", [])
        if not isinstance(names, list):
            raise ValueError("file_params.uploads 必须为参数名列表")
        uploads = [value for name in names if (value := parameter(name)) is not None]
        options = {key: parameter(name) for key, name in mapping.items() if key != "uploads"}
        return cls(upload_files=uploads, **{key: value for key, value in options.items() if value is not None})

    def available(self):
        return [{"id": key, "name": path.name} for key, path in self.uploads.items()]

    def resolve_uploads(self, paths=None, file_ids=None):
        if (paths is None) == (file_ids is None):
            raise ValueError("上传必须指定 file_ids 或 paths，且只能选一种；先通过 Skill 声明的 --param 文件参数选择文件")
        values = file_ids if file_ids is not None else paths
        values = [values] if isinstance(values, str) else values
        if not isinstance(values, list) or not values or not all(isinstance(x, str) for x in values):
            raise ValueError("上传文件必须是非空字符串列表")
        selected = []
        for value in values:
            if file_ids is not None:
                if value not in self.uploads:
                    raise ValueError(f"未选择的上传文件编号：{value}")
                path = self.uploads[value]
            else:
                path = Path(value)
                path = (path if path.is_absolute() else self.upload_dir / path).resolve()
            if path not in self.uploads.values() or path.resolve(strict=True) != path or not path.is_file():
                raise ValueError(f"文件未获本次选择或已变化，请使用 Skill 声明的 --param 文件参数明确指定：{path}")
            selected.append(str(path))
        return selected


class Files:
    def __init__(self, session, options):
        self.s = session
        self.options = options

    def prepare(self, name, args):
        args = dict(args)
        if name == "upload":
            args["paths"] = self.options.resolve_uploads(args.get("paths"), args.pop("file_ids", None))
        elif name == "download":
            chosen = self.options.download_name or args.get("filename")
            if chosen is not None:
                args["filename"] = validate_filename(chosen)
        return args

    def upload(self, target, paths):
        files = self.options.resolve_uploads(paths=paths)
        progress("准备选择上传文件：\n" + "\n".join(files))
        self.s.target(target).set_input_files(files)
        progress("文件已选入网页控件；是否上传完成需以网页结果为准。")
        return {"selected_files": [Path(path).name for path in files], "paths": files}

    def download(self, target, filename=None):
        directory = self.options.download_dir
        directory.mkdir(parents=True, exist_ok=True)
        filename = self.options.download_name or filename
        if filename is not None:
            validate_filename(filename)
        with self.s.current().expect_download(timeout=30_000) as pending:
            self.s.target(target).click()
        download = pending.value
        name = validate_filename(filename or download.suggested_filename)
        path = directory / name
        # 自动避开同名文件，不覆盖用户已有下载。
        number = 1
        while True:
            try:
                with path.open("xb"):
                    pass
                break
            except FileExistsError:
                path = directory / f"{Path(name).stem}-{number}{Path(name).suffix}"
                number += 1
        try:
            download.save_as(path)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        error = download.failure()
        if error:
            path.unlink(missing_ok=True)
            raise RuntimeError(error)
        progress(f"下载已保存：{path}")
        return {"path": str(path), "bytes": path.stat().st_size}
