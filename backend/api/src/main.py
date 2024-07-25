if __name__ == "__main__":
    import uvicorn
    from pathlib import Path

    dir_ = Path().expanduser().resolve().parent
    env_path = dir_.joinpath("../.env").resolve()
    reload_dir = dir_.joinpath("../").resolve()
    uvicorn.run("api:app", host="127.0.0.1", port=8000, env_file=str(env_path))
