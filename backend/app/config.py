from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    roms_dir: str = "../roms"
    db_path: str = "./data/library.db"
    emulators_dirname: str = "emulator"

    ss_devid: str = ""
    ss_devpassword: str = ""
    ss_softname: str = "serpentarium"
    ss_ssid: str = ""
    ss_sspassword: str = ""

    igdb_client_id: str = ""
    igdb_client_secret: str = ""

    @property
    def screenscraper_configured(self) -> bool:
        return bool(self.ss_devid and self.ss_devpassword and self.ss_ssid and self.ss_sspassword)

    @property
    def igdb_configured(self) -> bool:
        return bool(self.igdb_client_id and self.igdb_client_secret)


settings = Settings()
