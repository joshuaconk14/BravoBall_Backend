from functools import lru_cache
from models import Settings
from pydantic import BaseModel, ValidationError

@lru_cache
def get_settings():
    # print("get settings called")
    try:
        return Settings()
    except ValidationError as exc:
        print("Validation Error:", exc.errors())
        raise