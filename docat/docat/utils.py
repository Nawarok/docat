"""
docat utilities
"""
import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile

from jinja2 import Template

NGINX_CONFIG_PATH = Path("/etc/nginx/locations.d")
UPLOAD_FOLDER = Path("/var/docat/doc")


def create_symlink(source, destination):
    """
    Create a symlink from source to destination, if the
    destination is already a symlink, it will be overwritten.

    Args:
        source (pathlib.Path): path to the source
        destination (pathlib.Path): path to the destination
    """
    if not destination.exists() or (destination.exists() and destination.is_symlink()):
        if destination.is_symlink():
            destination.unlink()  # overwrite existing tag
        destination.symlink_to(source)
        return True
    else:
        return False


def create_nginx_config(project, project_base_path):
    """
    Creates an Nginx configuration for an uploaded project
    version.

    Args:
        project (str): name of the project
        project_base_path (pathlib.Path): base path of the project
    """
    nginx_config = NGINX_CONFIG_PATH / f"{project}-doc.conf"
    if not nginx_config.exists():
        out_parsed_template = Template((Path(__file__).parent / "templates" / "nginx-doc.conf").read_text()).render(
            project=project, dir_path=str(project_base_path)
        )
        with nginx_config.open("w") as f:
            f.write(out_parsed_template)

        subprocess.run(["nginx", "-s", "reload"])


def extract_archive(target_file, destination):
    """
    Extracts the given archive to the directory
    and deletes the source afterwards.

    Args:
        target_file (pathlib.Path): target archive
        destination: (pathlib.Path): destination of the extracted archive
    """
    if target_file.suffix == ".zip":
        # this is required to extract zip files created
        # on windows machines (https://stackoverflow.com/a/52091659/12356463)
        os.path.altsep = "\\"
        with ZipFile(target_file, "r") as zipf:
            zipf.extractall(path=destination)
        target_file.unlink()  # remove the zip file


def remove_docs(project, version):
    """
    Delete documentation

    Args:
        project (str): name of the project
        version (str): project version
    """
    docs = UPLOAD_FOLDER / project / version
    if not docs.exists():
        return f"Could not find version '{docs}'"
    # remove the requested version
    # rmtree can not remove a symlink
    if docs.is_symlink():
        docs.unlink()
    else:
        shutil.rmtree(docs)

    # remove dead symlinks
    for link in (s for s in docs.parent.iterdir() if s.is_symlink()):
        if not link.resolve().exists():
            link.unlink()

    # remove empty projects
    if not [d for d in docs.parent.iterdir() if d.is_dir()]:
        docs.parent.rmdir()
        nginx_config = NGINX_CONFIG_PATH / f"{project}-doc.conf"
        if nginx_config.exists():
            nginx_config.unlink()


def calculate_token(password, salt):
    """
    Wrapper function for pbkdf2_hmac to ensure consistent use of
    hash digest algorithm and iteration count.

    Args:
        password (str): the password to hash
        salt (byte): the salt used for the password
    """
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000).hex()
