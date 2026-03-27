import argparse

from src.lucidpanda.core.database import IntelligenceDB


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill expectation_gap and alpha_return in intelligence."
    )
    parser.add_argument(
        "--limit", type=int, default=500, help="Max rows to backfill per metric."
    )
    parser.add_argument(
        "--window", type=int, default=200, help="Window size for alpha regression."
    )
    args = parser.parse_args()

    db = IntelligenceDB()
    gap_updated = db.backfill_expectation_gap(limit=args.limit)
    alpha_updated = db.backfill_alpha_return(limit=args.limit, window=args.window)

    print(f"expectation_gap updated: {gap_updated}")
    print(f"alpha_return updated: {alpha_updated}")


if __name__ == "__main__":
    main()
