"""
iOSpy CLI
"""
from pathlib import Path
from typing import Union
import logging

import click

from . import __version__, mobilesync

logger = logging.getLogger("ios")


@click.group(help=__doc__)
@click.version_option(__version__)
@click.option("-v", "--verbose", count=True, help="Increase logging verbosity.")
@click.option(
    "--manifest",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to manifest. [defaults to latest]",
    default=mobilesync.latest_manifest(),
)
@click.pass_context
def cli(ctx: click.Context, verbose: int, manifest: Union[Path, str, None]):
    logging_format = "%(asctime)14s %(levelname)-7s %(name)s - %(message)s"
    logging_level = logging.INFO - (verbose * 10)
    logging_level_name = logging.getLevelName(logging_level)
    logging.basicConfig(format=logging_format, level=logging_level)
    logger.debug("Set logging level to %s [%d]", logging_level_name, logging_level)
    # initialize & populate context "user object"
    ctx.ensure_object(dict)
    ctx.obj["manifest"] = manifest


@cli.command()
def manifests():
    """
    Print known Manifest.db files.
    """
    logger.info("Listing manifests")
    for path in mobilesync.iter_manifests():
        print(path)


@cli.command()
@click.pass_context
def domains(ctx: click.Context):
    """
    Print unique domains from manifest.
    """
    manifest = ctx.obj["manifest"]
    logger.info("Listing domains from manifest at %s", manifest)
    for domain in mobilesync.iter_domains(manifest):
        print(domain)


@cli.command()
@click.option("--domain", type=str, help="Limit to specific domain.")
@click.pass_context
def files(ctx: click.Context, domain: str):
    """
    Print files from manifest.

    Output is TSV format with columns:
    1. fileID
    2. domain
    3. relativePath
    """
    manifest = ctx.obj["manifest"]
    logger.info("Listing files from manifest at %s", manifest)
    for file in mobilesync.iter_files(manifest, domain):
        fileID = file["fileID"]
        domain = file["domain"]
        relativePath = file["relativePath"]
        print(fileID, domain, relativePath, sep="\t")


@cli.command()
@click.option("--domain", type=str, help="Limit to specific domain.")
@click.option("--post/--raw", help="Run postprocessing on written files.")
@click.option(
    "--output",
    type=click.Path(exists=True, file_okay=False),
    help="Directory to write file structure into. [defaults to current directory]",
    default=".",
)
@click.pass_context
def rebuild(ctx: click.Context, domain: str, post: bool, output: str):
    """
    Copy and rename files from backup into `output`.

    Rebuilds the deep structure (creating directories as needed) specified by the
    manifest by copying the sha1-named files in the backup directory into filepaths
    like $output/$domain/path/to/file.txt

    Specifying a domain is recommended; otherwise it will copy ALL files!
    """
    manifest = ctx.obj["manifest"]
    logger.info("Rebuilding file structure from manifest at %s", manifest)
    mobilesync.rebuild(manifest, domain=domain, target=output, postprocess_files=post)


main = cli.main

if __name__ == "__main__":
    main(prog_name="ios")
