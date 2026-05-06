class DummyTask:
    def delay(self, document_id: str, tenant_id: str, file_path: str):
        print(
            "Document processing placeholder: "
            f"document_id={document_id}, "
            f"tenant_id={tenant_id}, "
            f"file_path={file_path}"
        )


process_document = DummyTask()
