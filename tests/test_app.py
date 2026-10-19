from minilms.app import create_app


def test_home_returns_expected_json() -> None:
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == {
        "name": "Mini LMS",
        "message": "Chào mừng đến với hệ thống quản lý học tập.",
    }


def test_unknown_route_returns_404() -> None:
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        response = client.get("/route-that-does-not-exist")

    assert response.status_code == 404
