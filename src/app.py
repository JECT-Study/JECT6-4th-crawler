import argparse
from src.controllers.crawl_controller import CrawlController


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--site",
        choices=["reviewnote", "gugudas", "blog", "all"],
        default="all",
    )
    parser.add_argument("--url", help="Target URL for site=blog")
    args = parser.parse_args()

    controller = CrawlController()

    if args.site == "reviewnote":
        controller.run_reviewnote()
    elif args.site == "gugudas":
        controller.run_gugudas()
    elif args.site == "blog":
        controller.run_blog(source=args.url)
    else:
        controller.run_all()


if __name__ == "__main__":
    main()