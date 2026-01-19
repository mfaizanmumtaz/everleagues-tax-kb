"""Custom exceptions for the File Parser Service."""


class FileParserError(Exception):
    """Base exception for all file parser errors."""

    def __init__(self, message: str, filename: str = "", details: str = ""):
        self.message = message
        self.filename = filename
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        parts = [self.message]
        if self.filename:
            parts.append(f"File: {self.filename}")
        if self.details:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)


class UnsupportedFileTypeError(FileParserError):
    """Raised when attempting to parse an unsupported file type."""

    def __init__(self, filename: str, file_type: str, supported_types: list = None):
        self.file_type = file_type
        self.supported_types = supported_types or []

        message = f"Unsupported file type: {file_type}"
        if self.supported_types:
            message += f". Supported types: {', '.join(self.supported_types)}"

        super().__init__(message=message, filename=filename)


class ExtractionError(FileParserError):
    """Raised when text extraction fails."""

    def __init__(
        self, filename: str, loader_name: str = "", original_error: Exception = None
    ):
        self.loader_name = loader_name
        self.original_error = original_error

        message = "Failed to extract text from file"
        if loader_name:
            message += f" using {loader_name}"

        details = ""
        if original_error:
            details = str(original_error)

        super().__init__(message=message, filename=filename, details=details)


class LoaderNotFoundError(FileParserError):
    """Raised when a required LangChain loader cannot be found or imported."""

    def __init__(self, loader_name: str, package: str = "", install_hint: str = ""):
        self.loader_name = loader_name
        self.package = package
        self.install_hint = install_hint

        message = f"Loader '{loader_name}' not found"
        if package:
            message += f" in package '{package}'"

        details = ""
        if install_hint:
            details = f"Install hint: {install_hint}"

        super().__init__(message=message, details=details)


class FileNotFoundError(FileParserError):
    """Raised when the file to parse cannot be found."""

    def __init__(self, filepath: str):
        super().__init__(message=f"File not found: {filepath}", filename=filepath)


class EmptyFileError(FileParserError):
    """Raised when the file is empty or contains no extractable content."""

    def __init__(self, filename: str):
        super().__init__(
            message="File is empty or contains no extractable text", filename=filename
        )
