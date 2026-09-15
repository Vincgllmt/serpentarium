from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    roms_dir: str = "../roms"
    db_path: str = "./data/library.db"
    covers_dir: str = "./data/covers"
    emulators_dirname: str = "emulator"

    ss_devid: str = ""
    ss_devpassword: str = ""
    ss_softname: str = "serpentarium"
    ss_ssid: str = ""
    ss_sspassword: str = ""
    # api2.screenscraper.fr est en panne DNS depuis un moment (probleme connu
    # cote ScreenScraper) ; www.screenscraper.fr sert le meme /api2/*.
    ss_base_url: str = "https://www.screenscraper.fr/api2"
    # Compte non-donateur = 1 seul thread autorise en parallele : on serialise
    # nos appels avec un delai mini entre deux requetes pour ne pas se faire
    # bannir / mettre en file d'attente cote serveur.
    ss_min_interval_seconds: float = 2.0
    ss_timeout_seconds: float = 30.0
    ss_max_retries: int = 3

    igdb_client_id: str = ""
    igdb_client_secret: str = ""

    @property
    def screenscraper_configured(self) -> bool:
        return bool(self.ss_devid and self.ss_devpassword and self.ss_ssid and self.ss_sspassword)

    @property
    def igdb_configured(self) -> bool:
        return bool(self.igdb_client_id and self.igdb_client_secret)


settings = Settings()
