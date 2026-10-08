class PipelineError(Exception):
    """A user-presentable failure in one stage of the pipeline."""

    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage
        self.message = message
