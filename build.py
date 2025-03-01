import lxml.etree as ET
import os
import argparse
import shutil
import html
import re
import watchdog.events
import watchdog.observers
import time

WEBSITE_PREFIX = "https://aaa-gaming-company.github.io"
OUTPUT_DIR = "./dist"
PUBLIC_DIR = "./public"
TEMPLATES = {
    "html": "./templates/page.html",
}

# --- Utility functions ---

def read_file(file_path: str) -> str:
    with open(file_path, "r") as file:
        return file.read()
    
def write_file(file_path: str, contents: str):
    with open(file_path, "w") as file:
        file.write(contents)

# --- Cleanup functions ---

def clean_output():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)

def ensure_output_exists():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

# --- Sync functions ---

def sync_deleted_files(source: str, destination: str):
    """
    Deletes files from the output directory that no longer exist in the source directory.
    """

    if not os.path.exists(destination):
        return

    if os.path.isfile(destination) and not os.path.exists(source):
        os.unlink(destination)
        return

    if not os.path.exists(source):
        shutil.rmtree(destination)
        return

    for file in os.listdir(destination):
        source_path = os.path.join(source, file)
        destination_path = os.path.join(destination, file)

        if not os.path.exists(source_path):
            if os.path.isfile(destination_path):
                os.unlink(destination_path)
            elif os.path.isdir(destination_path):
                shutil.rmtree(destination_path)
        elif os.path.isdir(destination_path):
            sync_deleted_files(source_path, destination_path)

def is_source_newer(source: str, destination: str) -> bool:
    if not os.path.exists(destination):
        return True

    source_time = os.path.getmtime(source)
    destination_time = os.path.getmtime(destination)

    return source_time > destination_time

def merge_files(source: str, destination: str) -> set:
    """
    Copies the files and folders that don't exist and merges the folders that do.\n
    If a file exists in both source and destination the source file is copied over the destination file.
    """

    if not os.path.exists(source):
        return set()

    if os.path.isfile(source):
        if is_source_newer(source, destination):
            shutil.copy(source, destination)
            return {destination}
        return set()

    if not os.path.exists(destination):
        os.makedirs(destination)

    changes = set()

    for file in os.listdir(source):
        source_path = os.path.join(source, file)
        destination_path = os.path.join(destination, file)

        if os.path.isfile(source_path):
            # Don't bother with files that are not newer
            if not is_source_newer(source_path, destination_path):
                continue

            shutil.copy(source_path, destination_path)
            changes.add(destination_path)
        elif os.path.isdir(source_path):
            if not os.path.exists(destination_path):
                shutil.copytree(source_path, destination_path)
                changes.add(destination_path)
            else:
                changes.update(merge_files(source_path, destination_path))

    return changes

# --- Build functions ---

def build_html_file(file_path: str) -> bool:
    """
    Merges the given HTML file with the template.\n
    \n
    This function takes the template file as a base and finds elements in the given file to replace the template elements.\n
    Go the deepest possible and append to the last common parent.
    """

    assert os.path.exists(file_path), f"File {file_path} does not exist!"
    assert os.path.exists(TEMPLATES["html"]), f"Template file {TEMPLATES['html']} does not exist!"

    source = read_file(file_path)
    if source.startswith("<!--RAW-->"):
        write_file(file_path.replace(PUBLIC_DIR, OUTPUT_DIR), source.replace("<!--RAW-->", ""))
        return True

    # Read the contents of the file
    source_tree = None
    output_tree = None
    try:
        source = re.sub("\\&\\w+\\;", lambda x: html.escape(html.unescape(x.group(0))), source)
        source_tree = ET.fromstring(source)
    except ET.ParseError as e:
        print(f"\nError parsing file {file_path}: {e}")
        return False
    try:
        output = re.sub("\\&\\w+\\;", lambda x: html.escape(html.unescape(x.group(0))), read_file(TEMPLATES["html"]))
        output_tree = ET.fromstring(output)
    except ET.ParseError as e:
        print(f"\nError parsing template file {TEMPLATES['html']}: {e}")
        return False

    # Find the elements in the file that are the last in common with the template
    def find_last_common_pairs(source: ET.Element, output: ET.Element) -> list:
        pairs = []

        source_children = list(source)
        output_children = list(output)

        if len(source_children) == 0 or len(output_children) == 0:
            if source.tag == output.tag:
                return [(source, output)]
            else:
                return []

        for src_chld in source_children:
            tag_found = False

            for out_chld in output_children:
                if src_chld.tag == out_chld.tag:
                    pairs.extend(find_last_common_pairs(src_chld, out_chld))
                    tag_found = True
                    break

            if not tag_found:
                pairs.append((src_chld, output))

        return pairs

    element_pairs = find_last_common_pairs(source_tree, output_tree)

    # Append the contents of the source elements to the output elements
    for source, output in element_pairs:
        if len(list(source)) > 0:
            output.extend(source)
        else:
            output.text = source.text

    # Write the output to the file
    raw_code = "<!DOCTYPE html>\n" + ET.tostring(output_tree, pretty_print=True, encoding="unicode", method="html")
    write_file(file_path.replace(PUBLIC_DIR, OUTPUT_DIR), raw_code)

    return True

def build_file(file_path: str) -> bool:
    """
    Builds the given file.
    """

    extension = ""
    if "." in file_path:
        extension = file_path.split(".")[-1]

    if extension == "html":
        return build_html_file(file_path)

    return True

def build_folder(path: str) -> bool:
    """
    Recursively builds the files in the given folder.
    """

    for file in os.listdir(path):
        file_path = os.path.join(path, file)

        # Ignore what isn't a file
        if os.path.isfile(file_path):
            if not build_file(file_path):
                return False
        elif os.path.isdir(file_path):
            if not build_folder(file_path):
                return False

    return True

def build_changes(changes: list) -> bool:
    for change in changes:
        print(change)

        if os.path.isfile(change):
            if not build_file(change):
                print(f"Failed to build file {change}")
                return False
        elif os.path.isdir(change):
            if not build_folder(change):
                print(f"Failed to build folder {change}")
                return False
            
    return True

def build_sitemap():
    """
    Builds the sitemap.xml file.
    """

    sitemap = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    for root, _, files in os.walk(OUTPUT_DIR):
        for file in files:
            file_path = os.path.join(root, file)

            if file_path.endswith(".html") or file_path.endswith(".svg") or file_path.endswith(".png") or file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
                is_image = file_path.endswith(".svg") or file_path.endswith(".png") or file_path.endswith(".jpg") or file_path.endswith(".jpeg")

                url = ET.SubElement(sitemap, "url")

                location = WEBSITE_PREFIX + file_path.replace(OUTPUT_DIR, "").replace("\\", "/")
                if location.endswith("/index.html"):
                    location = location[:-10]

                ET.SubElement(url, "loc").text = location
                ET.SubElement(url, "lastmod").text = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime(os.path.getmtime(file_path)))
                ET.SubElement(url, "priority").text = "0.50" if is_image else "0.80"

    # Set the root element priority to 1.00
    assert sitemap[0][0].text == WEBSITE_PREFIX + "/"
    sitemap[0][2].text = "1.00"

    write_file(os.path.join(OUTPUT_DIR, "sitemap.xml"), "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + ET.tostring(sitemap, pretty_print=True, encoding="unicode"))

# --- Watch functions ---

class WatchHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, watch_path: str = PUBLIC_DIR):
        super().__init__()

        self.watch_path = os.path.abspath(watch_path)

    def build(self, path: str):
        output_path = path.replace(os.path.abspath(PUBLIC_DIR), os.path.abspath(OUTPUT_DIR))
        merge_files(path, output_path)

        if os.path.isfile(output_path):
            build_file(output_path)
        elif os.path.isdir(output_path):
            build_folder(output_path)
    
    def local_path(self, path: str) -> str:
        return os.path.abspath(path).replace(os.path.abspath(self.watch_path) + "/", "./")

    def on_modified(self, event):
        if event.is_directory:
            return

        print(f'Updating {self.local_path(event.src_path)}')
        self.build(event.src_path)

    def on_created(self, event):
        print(f'Creating {self.local_path(event.src_path)}')
        self.build(event.src_path)

    def on_deleted(self, event):
        print(f'Deleted {self.local_path(event.src_path)}')
        sync_deleted_files(event.src_path, event.src_path.replace(os.path.abspath(PUBLIC_DIR), os.path.abspath(OUTPUT_DIR)))

def watch_for_changes():
    event_handler = WatchHandler()
    observer = watchdog.observers.Observer()
    observer.schedule(event_handler, path=PUBLIC_DIR, recursive=True)

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="Build script for the project")
    arg_parser.add_argument("--clean", action="store_true", help="Clean the build directory")
    arg_parser.add_argument("--deploy", type=str, help="Deploy the build to the server at the given path")
    arg_parser.add_argument("--watch", action="store_true", help="Watch for changes and rebuild")
    args = arg_parser.parse_args()

    if args.deploy and args.watch:
        print("Cannot deploy and watch!")
        exit(1)

    if args.clean:
        print("Cleaning...")
        clean_output()
    ensure_output_exists()

    print("Propagating changes...")
    sync_deleted_files(PUBLIC_DIR, OUTPUT_DIR)
    changes = merge_files(PUBLIC_DIR, OUTPUT_DIR)

    print("\nBuilding...")
    if build_changes(list(changes)):
        build_sitemap()

        print("\nBuilt successfully!")

        if args.deploy:
            print("\nDeploying...")
            if not os.path.exists(args.deploy):
                os.makedirs(args.deploy)

            sync_deleted_files(OUTPUT_DIR, args.deploy)
            merge_files(OUTPUT_DIR, args.deploy)
            print("Deployed!")
    else:
        print("\nFailed to build!")
    
    if args.watch:
        print("\nWatching for changes...")
        watch_for_changes()
        print("\nStopped watching.")