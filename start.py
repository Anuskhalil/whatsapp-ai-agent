import uvicorn

from app.config import (
    APP_HOST,
    APP_PORT
)


def main():

    uvicorn.run(
        "app.main:app",
        host=APP_HOST,
        port=APP_PORT,
        workers=1,
        reload=False
    )


if __name__ == "__main__":

    main()