from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str
    age: int | None = None
    is_active: bool = Field(default=True, sa_column_kwargs={"server_default": "1"})
