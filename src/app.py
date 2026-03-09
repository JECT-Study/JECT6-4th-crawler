import argparse
from src.controllers.crawl_controller import CrawlController


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", choices=["reviewnote", "gugudas", "all"], default="all")
    args = parser.parse_args()

    controller = CrawlController()

    if args.site == "reviewnote":
        controller.run_reviewnote()
    elif args.site == "gugudas":
        controller.run_gugudas()
    else:
        controller.run_all()


if __name__ == "__main__":
    main()