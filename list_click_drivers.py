#!/usr/bin/env python3

import os
import glob
from difflib import SequenceMatcher
from collections import defaultdict


def get_similarity(a, b):
    # Custom similarity scoring that favors exact substring matches
    a = a.lower()
    b = b.lower()

    # Direct match gets highest score
    if a == b:
        return 1.0

    # If one string contains the other completely, give it a high score
    if a in b or b in a:
        return 0.9

    # For partial matches, use sequence matcher
    return SequenceMatcher(None, a, b).ratio()


def find_binding_matches(driver_name):
    # Base path for Zephyr bindings
    ZEPHYR_BINDINGS = "/Users/kartben/zephyrproject/zephyr/dts/bindings"

    # Expanded list of directories to search for bindings
    binding_dirs = [
        "sensor",
        "i2c",
        "spi",
        "iio",
        "display",
        "rtc",
        "mmc",
        "ethernet",
        "input",
        "gpio",
        "pwm",
        "adc",
        "led",
        "counter",
    ]

    # Get all yaml files from binding directories
    binding_files = []
    for dir_name in binding_dirs:
        dir_path = os.path.join(ZEPHYR_BINDINGS, dir_name)
        if os.path.exists(dir_path):
            binding_files.extend(glob.glob(f"{dir_path}/*.yaml"))

    # Process each binding file
    matches = []
    seen_names = set()  # To avoid duplicate base names

    for file_path in binding_files:
        # Get filename without extension
        full_name = os.path.splitext(os.path.basename(file_path))[0]

        # Handle different name formats
        if "," in full_name:
            vendor, name = full_name.split(",", 1)
            name = name.strip()

            # Skip if we've seen this base name
            if name in seen_names:
                continue
            seen_names.add(name)

            # Remove common suffixes
            for suffix in ["-i2c", "-spi", "-common"]:
                if name.endswith(suffix):
                    name = name[: -len(suffix)]

            # Calculate similarity
            similarity = get_similarity(driver_name, name)

            # Only include matches above threshold
            if similarity >= 0.6:
                matches.append((file_path, similarity, vendor))

    # Sort by similarity score in descending order
    matches.sort(key=lambda x: x[1], reverse=True)

    # Return top 3 matches
    return matches[:3]


def extract_driver_info(manifest_file):
    folder_name = os.path.basename(os.path.dirname(os.path.dirname(manifest_file)))
    driver_name = None

    with open(manifest_file, "r") as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if "[string-descriptor 3]" in line and i + 1 < len(lines):
                driver_line = lines[i + 1].strip()
                if driver_line.startswith("string = "):
                    driver_name = driver_line[8:].strip()
                    break

    if driver_name:
        return folder_name, driver_name
    return None


def main():
    # Get all manifest files
    manifest_files = glob.glob("clicks/*/manifest/*.mnfs")
    manifest_files.extend(glob.glob("clicks/UNTESTED/*/manifest/*.mnfs"))

    # Extract and store results
    results = []
    perfect_matches = []
    no_matches = []
    match_by_score = defaultdict(list)

    for manifest_file in manifest_files:
        info = extract_driver_info(manifest_file)
        if info:
            folder_name, driver_name = info
            binding_matches = find_binding_matches(driver_name)
            results.append((folder_name, driver_name, binding_matches))

            # Track statistics
            if not binding_matches:
                no_matches.append((folder_name, driver_name))
            else:
                best_score = int(binding_matches[0][1] * 100)
                match_by_score[best_score].append((folder_name, driver_name))
                if best_score == 100:
                    perfect_matches.append(
                        (folder_name, driver_name, binding_matches[0])
                    )

    # Sort by folder name and print results
    results.sort(key=lambda x: x[0])
    for folder, driver, matches in results:
        print(f"{folder}, {driver}")
        if matches:
            print("  Possible bindings:")
            for binding_path, score, vendor in matches:
                # Format score as percentage
                score_pct = int(score * 100)
                # Show relative path from bindings directory
                rel_path = os.path.relpath(
                    binding_path, "/Users/kartben/zephyrproject/zephyr/dts/bindings"
                )
                print(f"    - [{score_pct}%] {vendor}: {rel_path}")
        print()

    # Print summary
    total_clicks = len(results)
    print("\n=== Summary ===")
    print(f"Total Click boards analyzed: {total_clicks}")
    print(
        f"Perfect matches (100%): {len(perfect_matches)} ({len(perfect_matches)/total_clicks*100:.1f}%)"
    )
    print("\nPerfect matches:")
    for folder, driver, (binding_path, _, vendor) in perfect_matches:
        rel_path = os.path.relpath(
            binding_path, "/Users/kartben/zephyrproject/zephyr/dts/bindings"
        )
        print(f"  - {folder} ({driver}) → {vendor}: {rel_path}")

    print("\nNo matches found for:")
    for folder, driver in no_matches:
        print(f"  - {folder} ({driver})")


if __name__ == "__main__":
    main()
