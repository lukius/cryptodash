import getpass

from backend.database import async_session, init_db


async def reset_password() -> None:
    await init_db()
    pw = getpass.getpass("New password: ")
    pw2 = getpass.getpass("Confirm password: ")
    if pw != pw2:
        print("Passwords do not match.")
        return
    if len(pw) < 8:
        print("Password must be at least 8 characters.")
        return

    # AuthService is implemented in T05; imported lazily so this module loads
    # without it being present yet.
    from backend.services.auth import AuthService  # noqa: PLC0415

    async with async_session() as db:
        service = AuthService(db)
        await service.reset_password(pw)
        await db.commit()

    print("Password updated. All sessions invalidated.")
