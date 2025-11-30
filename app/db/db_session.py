from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


def get_company_engine(db_path):
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine

def get_company_session(db_path: str):
    engine = get_company_engine(db_path)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
