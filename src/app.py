import argparse
from src.controllers.crawl_controller import CrawlController


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--site",
        choices=["assaview", "stylec", "all"],
        default="all",
    )
    args = parser.parse_args()

    controller = CrawlController()

    if args.site == "assaview":
        controller.run_assaview()
    elif args.site == "stylec":
        controller.run_stylec()
    else:
        controller.run_all()


if __name__ == "__main__":
    main()