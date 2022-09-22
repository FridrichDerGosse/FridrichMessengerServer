import sqlalchemy as db


# db setup
META = db.MetaData()
DB_NAME: str = "main.db"
ENGINE = db.create_engine(f'sqlite:///{DB_NAME}', echo=False)

EmptyUser = db.Table(
    "user", META,
    db.Column("id", db.Integer, primary_key=True),
    db.Column("username", db.String, nullable=False),
    db.Column("password", db.String, nullable=False),
)

EmptyMessage = db.Table(
    "message", META,
    db.Column("id", db.Integer, primary_key=True),
    db.Column("chat_id", db.Integer, nullable=False),
    db.Column("content", db.String, nullable=True),
    db.Column("time_sent", db.Float, nullable=False),
    db.Column("sent_from_id", db.String, nullable=False),
)

EmptyChat = db.Table(
    "chat", META,
    db.Column("id", db.Integer, primary_key=True),
    db.Column("name", db.String, nullable=False),
    db.Column("user_ids", db.JSON, nullable=False),
    db.Column("user_names", db.JSON, nullable=False),
)


def create_table():
    META.create_all(ENGINE)
