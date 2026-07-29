"""Kanameishi - エントリーポイント"""

from .app import EarthquakeApp


def main() -> None:
    app = EarthquakeApp()
    app.run()


if __name__ == "__main__":
    main()
