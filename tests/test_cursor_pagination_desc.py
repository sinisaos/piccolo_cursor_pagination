import typing as t
from unittest import TestCase

from fastapi import FastAPI, Request
from piccolo.columns import Integer, Varchar
from piccolo.columns.readable import Readable
from piccolo.table import Table
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from piccolo_cursor_pagination.pagination import CursorPagination


class Movie(Table):
    name = Varchar(length=100, required=True)
    rating = Integer()

    @classmethod
    def get_readable(cls):
        return Readable(template="%s", columns=[cls.name])


app = FastAPI()


@app.get("/movies/")
async def movies(
    request: Request,
    __cursor: str,
    __previous: t.Optional[str] = None,
):
    try:
        cursor = request.query_params["__cursor"]
        paginator = CursorPagination(
            cursor=cursor, page_size=1, order_by="-id"
        )
        rows_result, headers_result = await paginator.get_cursor_rows(
            Movie, request
        )
        rows = await rows_result.run()
        headers = headers_result
        response = JSONResponse(
            {"rows": rows[::-1]},
            headers={
                "next_cursor": headers["cursor"],
            },
        )
    except KeyError:
        cursor = request.query_params["__cursor"]
        paginator = CursorPagination(
            cursor=cursor, page_size=1, order_by="-id"
        )
        rows_result, headers_result = await paginator.get_cursor_rows(
            Movie, request
        )
        rows = await rows_result.run()
        headers = headers_result
        response = JSONResponse(
            {"rows": rows},
            headers={
                "next_cursor": headers["cursor"],
            },
        )
    return response


class TestCursorPaginationAsc(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_cursor_pagination_desc(self):
        """
        If cursor is applied
        """
        Movie.insert(
            Movie(name="Star Wars", rating=93),
            Movie(name="Lord of the Rings", rating=90),
        ).run_sync()

        client = TestClient(app)
        response = client.get("/movies/", params={"__cursor": ""})
        self.assertTrue(response.status_code, 200)
        self.assertEqual(response.headers["next_cursor"], "MQ==")
        self.assertEqual(
            response.json(),
            {
                "rows": [
                    {"id": 2, "name": "Lord of the Rings", "rating": 90},
                ]
            },
        )

    def test_cursor_pagination_desc_previous(self):
        """
        If cursor and previous is applied
        """
        Movie.insert(
            Movie(name="Star Wars", rating=93),
            Movie(name="Lord of the Rings", rating=90),
        ).run_sync()

        client = TestClient(app)
        response = client.get(
            "/movies/", params={"__cursor": "MQ==", "__previous": "yes"}
        )
        self.assertTrue(response.status_code, 200)
        self.assertEqual(response.headers["next_cursor"], "")
        self.assertEqual(
            response.json(),
            {
                "rows": [
                    {"id": 2, "name": "Lord of the Rings", "rating": 90},
                ]
            },
        )

    def test_cursor_pagination_desc_previous_no_more_results(self):
        """
        If cursor is empty and previous is applied there is no
        more results, return empty rows
        """
        Movie.insert(
            Movie(name="Star Wars", rating=93),
            Movie(name="Lord of the Rings", rating=90),
        ).run_sync()

        client = TestClient(app)
        response = client.get(
            "/movies/", params={"__cursor": "", "__previous": "yes"}
        )
        self.assertTrue(response.status_code, 200)
        self.assertEqual(response.headers["next_cursor"], "")
        self.assertEqual(
            response.json(),
            {"rows": []},
        )
