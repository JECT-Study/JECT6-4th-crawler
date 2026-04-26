def print_summary(site: str, count: int, file_path: str | None) -> None:
    print(f"[{site}] 수집 완료")
    print(f"- 수집 건수: {count}")
    if file_path:
        print(f"- 저장 경로: {file_path}")
