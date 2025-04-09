#!/usr/bin/env python3

import os
import shutil
import configparser
import re
import urllib.request
import urllib.error
import glob
from list_click_drivers import find_binding_matches, extract_driver_info
import subprocess
import textwrap
import html

ZEPHYR_BASE = os.path.expanduser("~/zephyrproject/zephyr")
SHIELDS_DIR = os.path.join(ZEPHYR_BASE, "boards/shields")
CLICKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clicks")


def parse_manifest(click_name):
    """Parse the manifest file for a Click board."""
    manifest_path = os.path.join(
        CLICKS_DIR, click_name, "manifest", f"{click_name}-CLICK.mnfs"
    )
    if not os.path.exists(manifest_path):
        print(f"Manifest file not found for {click_name} ; trying UNTESTED folder")
        manifest_path = os.path.join(
            CLICKS_DIR, "UNTESTED", click_name, "manifest", f"{click_name}-CLICK.mnfs"
        )
        if not os.path.exists(manifest_path):
            print(f"Manifest file not found for {click_name} in UNTESTED folder either")
            return None, None, None, None, None

    protocol = None
    reg = None
    irq = None
    mode = None
    max_speed = None

    current_section = None
    with open(manifest_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";"):
                continue

            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1]
                continue

            if current_section == "device-descriptor 1":
                if line.startswith("protocol = "):
                    protocol = line.split("=")[1].strip()
                elif line.startswith("reg = "):
                    reg = line.split("=")[1].strip()
                elif line.startswith("irq = "):
                    irq = line.split("=")[1].strip()
                elif line.startswith("mode = "):
                    mode = line.split("=")[1].strip()
                elif line.startswith("max-speed-hz = "):
                    max_speed = line.split("=")[1].strip()

    return protocol, reg, irq, mode, max_speed


def create_shield_directory(click_name):
    """Create a directory for the shield if it doesn't exist."""
    shield_name = f"mikroe_{click_name.lower().replace('-', '_')}_click"
    shield_dir = os.path.join(SHIELDS_DIR, shield_name)

    # Check if shield already exists
    if os.path.exists(shield_dir):
        return None, None

    os.makedirs(shield_dir, exist_ok=True)
    return shield_dir, shield_name


def create_kconfig_shield(shield_dir, shield_name, click_name):
    """Create Kconfig.shield file."""
    with open(os.path.join(shield_dir, "Kconfig.shield"), "w") as f:
        f.write(f"""# Copyright The Zephyr Project Contributors
# SPDX-License-Identifier: Apache-2.0

config SHIELD_{shield_name.upper()}
\tdef_bool $(shields_list_contains,{shield_name})
""")


def create_kconfig_defconfig(shield_dir, shield_name, driver):
    """Create Kconfig.defconfig file."""
    with open(os.path.join(shield_dir, "Kconfig.defconfig"), "w") as f:
        f.write(f"""# Copyright The Zephyr Project Contributors
# SPDX-License-Identifier: Apache-2.0

if SHIELD_{shield_name.upper()}

config {driver.upper()}
\tdefault y

endif # SHIELD_{shield_name.upper()}
""")


def create_overlay(
    shield_dir,
    shield_name,
    driver,
    click_name,
    protocol,
    reg,
    irq,
    mode,
    max_speed,
    binding,
):
    """Create shield overlay file."""
    # Extract vendor and compatible from binding
    vendor, _, binding_path = binding.partition(":")
    vendor = vendor.strip()
    binding_path = binding_path.strip()

    # Extract compatible from binding path
    # Format is typically "vendor: category/vendor,device.yaml"
    compatible = binding_path.split("/")[-1].replace(".yaml", "")
    # Remove interface suffix (-i2c or -spi) from compatible string
    compatible = compatible.replace("-i2c", "").replace("-spi", "")

    with open(os.path.join(shield_dir, f"{shield_name}.overlay"), "w") as f:
        f.write("/*\n")
        f.write(" * Copyright The Zephyr Project Contributors\n")
        f.write(" * SPDX-License-Identifier: Apache-2.0\n")
        f.write(" */\n\n")

        if protocol in ["0x3", "0x03"]:  # I2C
            reg_addr = int(reg, 16) if reg else 0
            f.write("&mikrobus_i2c {\n")
            f.write('\tstatus = "okay";\n\n')
            f.write(f"\t{driver}_{shield_name}: {driver}@{reg_addr:02x} {{\n")
            f.write(f'\t\tcompatible = "{compatible}";\n')
            f.write(f"\t\treg = <0x{reg_addr:02x}>;\n")
            if irq:
                f.write("\t\tint-gpios = <&mikrobus_header 7 GPIO_ACTIVE_LOW>;\n")
            f.write("\t};\n")
            f.write("};\n")
        elif protocol in ["0xb", "0x0b"]:  # SPI
            f.write("&mikrobus_spi {\n")
            f.write('\tstatus = "okay";\n\n')
            f.write(f"\t{driver}_{shield_name}: {driver}@0 {{\n")
            f.write(f'\t\tcompatible = "{compatible}";\n')
            f.write("\t\treg = <0>;\n")
            if max_speed:
                f.write(f"\t\tspi-max-frequency = <{max_speed}>;\n")
            if mode:
                mode_val = int(mode, 16)
                if mode_val & 0x2:
                    f.write("\t\tspi-cpol;\n")
                if mode_val & 0x1:
                    f.write("\t\tspi-cpha;\n")
            if irq:
                f.write("\t\tint-gpios = <&mikrobus_header 7 GPIO_ACTIVE_LOW>;\n")
            f.write("\t};\n")
            f.write("};\n")
        else:
            f.write(f"/* Protocol {protocol} not supported yet */\n")


def get_click_url(click_name):
    """Extract Click board URL from manifest file."""
    manifest_path = os.path.join(
        CLICKS_DIR, click_name, "manifest", f"{click_name}-CLICK.mnfs"
    )
    if not os.path.exists(manifest_path):
        return None

    with open(manifest_path, "r") as f:
        for line in f:
            if line.startswith("; https://"):
                return line.strip()[2:]
    return None


def get_schematic_url(click_name):
    """Extract schematic URL from Click board's webpage."""
    base_url = f"https://www.mikroe.com/{click_name.lower()}-click"
    try:
        # Add a user agent to avoid being blocked
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        req = urllib.request.Request(base_url, headers=headers)

        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8")
            # Look for the schematic download link
            pattern = r'<a class="btn-download" target="_blank" href="(https://download\.mikroe\.com/documents/add-on-boards/click/[^"]+schematic[^"]+\.pdf)">'
            match = re.search(pattern, html)
            if match:
                return match.group(1)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"Failed to fetch schematic URL for {click_name}: {e}")
    except Exception as e:
        print(f"Unexpected error while fetching schematic URL for {click_name}: {e}")
    return None


def get_overview_text(click_name):
    """Extract overview text from Click board's webpage."""
    base_url = f"https://www.mikroe.com/{click_name.lower()}-click"
    try:
        # Add a user agent to avoid being blocked
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        req = urllib.request.Request(base_url, headers=headers)

        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode("utf-8")
            # Look for the first paragraph in the info-description section
            pattern = r'<section id="info-description">\s*<p>(.*?)</p>'
            match = re.search(pattern, html_content, re.DOTALL)
            if match:
                # Clean up the HTML tags and extra whitespace
                text = match.group(1)
                text = re.sub(r"<[^>]+>", "", text)  # Remove HTML tags
                text = re.sub(r"\s+", " ", text)  # Normalize whitespace
                text = text.strip()
                # Unescape HTML entities
                text = html.unescape(text)
                # Wrap text to 100 characters
                text = textwrap.fill(text, width=100)
                return text
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"Failed to fetch overview text for {click_name}: {e}")
    except Exception as e:
        print(f"Unexpected error while fetching overview text for {click_name}: {e}")
    return None


def normalize_click_name(click_name):
    """Normalize Click board name for directory matching."""
    # Convert to lowercase
    name = click_name.lower()

    # Handle special cases first
    if name == "13dof-2":
        return ["13dof2", "13dof"]
    if name == "3d-hall-3":
        return ["3dhall3"]
    if name == "3d-hall-6":
        return ["3dhall6"]
    if name == "6dof-imu-2":
        return ["6dofimu2"]
    if name == "ir-thermo-2":
        return ["irthermo2"]
    if name == "temp-hum-12":
        return ["temphum12"]
    if name == "temp-hum-3":
        return ["temphum3"]
    if name == "temp-hum-8":
        return ["temphum8"]
    if name == "air-quality-3":
        return ["airquality3"]
    if name == "air-quality-5":
        return ["airquality5"]
    if name == "eth-wiz":
        return ["ethwiz", "wiznet"]
    if name == "eth":
        return ["eth", "ethernet"]
    if name == "lightranger-2":
        return ["lightranger2"]
    if name == "proximity-9":
        return ["proximity9"]
    if name == "thermo-12":
        return ["thermo12", "thermo", "surface-temp"]

    # General normalization
    # Remove dashes and spaces
    name = name.replace("-", "").replace(" ", "")
    return [name]


def copy_click_image(click_name, shield_dir, shield_name):
    """Copy Click board image from MikroSDK repository and convert to WebP."""
    # Create doc/images directory if it doesn't exist
    img_dir = os.path.join(shield_dir, "doc", "images")
    os.makedirs(img_dir, exist_ok=True)

    # Remove any existing PNG files for this shield
    png_path = os.path.join(img_dir, f"{shield_name}.png")
    if os.path.exists(png_path):
        os.remove(png_path)

    # Look for image in MikroSDK repository
    mikrosdk_dir = os.path.expanduser("~/Repositories/mikrosdk_click_v2/clicks")

    # Try different directory name variations
    dir_variations = [
        click_name.lower(),  # Original lowercase
        click_name.lower().replace("-", ""),  # No dashes
    ]
    dir_variations.extend(normalize_click_name(click_name))  # Add normalized variations

    # Remove duplicates while preserving order
    dir_variations = list(dict.fromkeys(dir_variations))

    # Try different image paths for each directory variation
    for dir_name in dir_variations:
        click_dir = os.path.join(mikrosdk_dir, dir_name)
        if not os.path.exists(click_dir):
            continue

        # Try different image paths
        image_paths = [
            os.path.join(click_dir, "doc", "image", "click_icon.png"),
            os.path.join(click_dir, "doc", "images", "click_icon.png"),
            os.path.join(click_dir, "doc", "image", f"{dir_name}.png"),
            os.path.join(click_dir, "doc", "image", f"{dir_name}-click.png"),
            os.path.join(click_dir, "doc", "images", f"{dir_name}.png"),
            os.path.join(click_dir, "doc", "images", f"{dir_name}-click.png"),
            os.path.join(click_dir, "image", "click_icon.png"),
            os.path.join(click_dir, "images", "click_icon.png"),
        ]

        for src_path in image_paths:
            if os.path.exists(src_path):
                # Convert to WebP using the shield name
                dst_path = os.path.join(img_dir, f"{shield_name}.webp")
                cmd = f"cwebp -quiet -q 80 {src_path} -o {dst_path}"
                try:
                    subprocess.run(
                        cmd,
                        shell=True,
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return True
                except subprocess.CalledProcessError as e:
                    print(f"Failed to convert image for {click_name}: {e}")
                    return False

    return False


def create_doc(shield_dir, shield_name, click_name, protocol):
    """Create documentation file."""
    # Ensure doc directory exists
    doc_dir = os.path.join(shield_dir, "doc")
    os.makedirs(doc_dir, exist_ok=True)

    # Check if WebP image exists
    img_path = os.path.join("images", f"{shield_name}.webp")
    has_image = os.path.exists(os.path.join(doc_dir, img_path))

    # Get schematic URL and overview text
    schematic_url = get_schematic_url(click_name)
    overview_text = get_overview_text(click_name)

    # Generate protocol-specific requirements text
    if protocol == "0x3":  # I2C
        requirements = """This shield can only be used with a board that provides a mikroBUS™ socket and defines a
``mikrobus_i2c`` node label for the mikroBUS™ I2C interface. See :ref:`shields` for more details."""
    elif protocol in ["0xb", "0x0b"]:  # SPI
        requirements = """This shield can only be used with a board that provides a mikroBUS™ socket and defines a
``mikrobus_spi`` node label for the mikroBUS™ SPI interface. See :ref:`shields` for more details."""
    else:
        # TODO ???
        requirements = """This shield can only be used with a board that provides a mikroBUS™ socket and defines either a
``mikrobus_i2c`` node label for the mikroBUS™ I2C interface or a ``mikrobus_spi`` node label for the
mikroBUS™ SPI interface. See :ref:`shields` for more details."""

    with open(os.path.join(doc_dir, "index.rst"), "w") as f:
        f.write(f""".. _{shield_name}:

MikroElektronika {click_name} Click
{'=' * (len(click_name) + 23)}

Overview
********

{overview_text if overview_text else f"The {click_name} Click shield carries a {click_name} board from MikroElektronika."}
""")

        if has_image:
            f.write(f"""
.. figure:: {img_path}
   :align: center
   :alt: {click_name} Click
   :height: 300px

   {click_name} Click
""")

        f.write(f"""
Requirements
************

{requirements}

Programming
**********

Set ``-DSHIELD={shield_name}`` when you invoke ``west build``. For example:

.. zephyr-app-commands::
   :zephyr-app: samples/sensor/sensor_shell
   :board: lpcxpresso55s16
   :shield: {shield_name}
   :goals: build

This will build the :zephyr:code-sample:`sensor_shell` sample which provides a quick way to verify
the shield is working correctly. After flashing, you can use the ``sensor`` command to list
available sensors and read their values.

References
**********

- `{click_name} Click webpage`_
""")

        if schematic_url:
            f.write(f"- `{click_name} Click schematic`_\n")

        f.write(f"""
.. _{click_name} Click webpage: https://www.mikroe.com/{click_name.lower()}-click
""")

        if schematic_url:
            f.write(f".. _{click_name} Click schematic: {schematic_url}\n")


def get_perfect_matches():
    """Get perfect matches from list_click_drivers.py results."""
    # Get all manifest files
    manifest_files = []
    manifest_files.extend(
        glob.glob(os.path.join(CLICKS_DIR, "*", "manifest", "*.mnfs"))
    )
    manifest_files.extend(
        glob.glob(os.path.join(CLICKS_DIR, "UNTESTED", "*", "manifest", "*.mnfs"))
    )

    perfect_matches = {}
    for manifest_file in manifest_files:
        info = extract_driver_info(manifest_file)
        if info:
            folder_name, driver_name = info
            binding_matches = find_binding_matches(driver_name)
            if binding_matches and binding_matches[0][1] == 1.0:  # Perfect match
                binding_path, _, vendor = binding_matches[0]
                # Format binding path as "vendor: path/to/binding.yaml"
                binding = f"{vendor}: {os.path.relpath(binding_path, os.path.join(ZEPHYR_BASE, 'dts/bindings'))}"
                perfect_matches[folder_name.upper()] = {
                    "driver": driver_name,
                    "binding": binding,
                }

    return perfect_matches


def main():
    """Main function to generate shield definitions."""
    perfect_matches = get_perfect_matches()
    clicks_without_images = []
    skipped_shields = []

    for click_name, info in perfect_matches.items():
        shield_dir, shield_name = create_shield_directory(click_name)

        # Skip if shield already exists
        if shield_dir is None:
            skipped_shields.append(click_name)
            continue

        # Parse manifest file
        protocol, reg, irq, mode, max_speed = parse_manifest(click_name)

        # Create documentation directory
        os.makedirs(os.path.join(shield_dir, "doc"), exist_ok=True)

        # Create shield files
        create_kconfig_shield(shield_dir, shield_name, click_name)
        # create_kconfig_defconfig(shield_dir, shield_name, info["driver"])
        create_overlay(
            shield_dir,
            shield_name,
            info["driver"],
            click_name,
            protocol,
            reg,
            irq,
            mode,
            max_speed,
            info["binding"],
        )

        # Try to copy image and track if not found
        if not copy_click_image(click_name, shield_dir, shield_name):
            clicks_without_images.append(click_name)

        # Create documentation
        create_doc(shield_dir, shield_name, click_name, protocol)

        print("=" * 80)
        print(f"Generated shield definition for {click_name} Click")
        print(
            f"Test with:\nwest build -b lpcxpresso55s16 --shield {shield_name} samples/sensor/sensor_shell -p"
        )

    # Print summary of clicks without images
    if clicks_without_images:
        print("\nNo images found for the following Click boards:")
        for click in sorted(clicks_without_images):
            print(f"  - {click}")

    # Print summary of skipped shields
    if skipped_shields:
        print("\nSkipped existing shields:")
        for click in sorted(skipped_shields):
            shield_name = f"mikroe_{click.lower().replace('-', '_')}_click"
            print(f"  - {click} (shield '{shield_name}' already exists)")


if __name__ == "__main__":
    main()
