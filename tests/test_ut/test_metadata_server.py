
def test_set(webapp):
    data = "kjkjdkjkjdkjfkdj"
    webapp.put("/api/v1/entities/a/b/c/d", data=data)
    assert webapp.get("/api/v1/entities/a/b/c/d") == {"result": data}

def test_get_raw(webapp):
    data = "kjkjdkjkjdkjfkdj"
    webapp.put("/api/v1/entities/a/b/c/d", data=data)
    assert webapp.get_raw("/api/v1/entities/a/b/c/d?raw=true").content == data
