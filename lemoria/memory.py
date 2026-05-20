from sqlalchemy.orm import Session
from database.models.conversation import Conversation, Message
from database.models.context import Context


class MemoryService:
    def __init__(self, session: Session):
        self.session = session

    def create_conversation(self, project_id: str, title: str | None = None, source: str = "cli") -> Conversation:
        conv = Conversation(project_id=project_id, title=title, source=source)
        self.session.add(conv)
        self.session.commit()
        return conv

    def add_message(self, conversation_id: str, role: str, content: str, token_count: int | None = None) -> Message:
        msg = Message(conversation_id=conversation_id, role=role, content=content, token_count=token_count)
        self.session.add(msg)
        self.session.commit()
        return msg

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        return self.session.get(Conversation, conversation_id)

    def list_conversations(self, project_id: str) -> list[Conversation]:
        return self.session.query(Conversation).filter(Conversation.project_id == project_id).all()

    def set_context(self, project_id: str, key: str, value: str, level: str = "project", priority: int = 0) -> Context:
        ctx = Context(project_id=project_id, key=key, value=value, level=level, priority=priority)
        self.session.add(ctx)
        self.session.commit()
        return ctx

    def get_context(self, project_id: str, level: str | None = None) -> list[Context]:
        query = self.session.query(Context).filter(Context.project_id == project_id)
        if level:
            query = query.filter(Context.level == level)
        return query.order_by(Context.priority.desc()).all()
