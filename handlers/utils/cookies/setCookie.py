def set_cookie(response, access_token, refresh):

    response.set_cookie(
        key="access_token",
        value=str(access_token),
        httponly=True,
        secure=True,
        samesite="None",
        path='/',
        max_age=60 * 10,
        expires=60 * 10,
    )

    response.set_cookie(
        key="refresh_token",
        value=str(refresh),
        httponly=True,
        secure=True,
        samesite="None",
        path='/',
        max_age=60 * 60 * 24 * 7, 
        expires=60 * 60 * 24 * 7,
    )

    response.set_cookie(
        key="isLoggedIn",
        value=bool(True),
        httponly=True,
        secure=True,
        samesite="None",
        path='/',
        max_age=60 * 10,
        expires=60 * 10,
    )