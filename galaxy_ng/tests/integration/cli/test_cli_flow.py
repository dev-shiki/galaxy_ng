"""test_cli_flow.py - Tests against the basic CLI publish/install behaviors."""
import logging
import pytest

from ..utils import ansible_galaxy
from ..utils import get_collection_full_path
from ..utils import CollectionInspector
from ..utils import build_collection
from ..utils.repo_management_utils import create_test_namespace

pytestmark = pytest.mark.qa  # noqa: F821
logger = logging.getLogger(__name__)


@pytest.mark.cli
@pytest.mark.all
@pytest.mark.skip_in_gw
@pytest.mark.usefixtures("cleanup_collections")
def test_publish_newer_version_collection(galaxy_client, uncertifiedv2):
    """Test whether a newer version of collection can be installed after being published.

    If the collection version was not certified the version to be installed
    has to be specified during installation.
    """
    # FIXME(jctanner): ^^^ is that really possible?
    v1 = uncertifiedv2[0]
    v2 = uncertifiedv2[1]
    gc = galaxy_client("basic_user")
    # Install collection without version ...
    install_pid = ansible_galaxy(
        f"collection install {v1.namespace}.{v1.name}",
        # ansible_config=ansible_config("basic_user"),
        galaxy_client=gc,
        cleanup=False,
        check_retcode=False
    )
    assert install_pid.returncode == 0, install_pid.stderr

    # Ensure the certified v1 version was installed ...
    collection_path = get_collection_full_path(v1.namespace, v1.name)
    ci = CollectionInspector(directory=collection_path)
    assert ci.version == v1.version
    assert ci.version != v2.version


@pytest.mark.all
@pytest.mark.cli
@pytest.mark.skip_in_gw
@pytest.mark.usefixtures("cleanup_collections")
def test_publish_newer_certified_collection_version(
    galaxy_client,
    certifiedv2,
    settings,
    skip_if_require_signature_for_approval
):
    """Test whether a newer certified collection version can be installed.

    If the collection version was certified the latest version will be installed.
    """

    v1 = certifiedv2[0]
    v2 = certifiedv2[1]
    gc = galaxy_client("basic_user")
    # Ensure v2 gets installed by default ...
    ansible_galaxy(
        f"collection install {v1.namespace}.{v1.name}",
        # ansible_config=ansible_config("basic_user")
        galaxy_client=gc
    )
    collection_path = get_collection_full_path(v1.namespace, v1.name)
    ci = CollectionInspector(directory=collection_path)
    assert ci.version != v1.version
    assert ci.version == v2.version


@pytest.mark.all
@pytest.mark.cli
@pytest.mark.skip(reason="pulp is changing how this works")
def test_publish_same_collection_version(ansible_config, galaxy_client):
    """Test you cannot publish same collection version already published."""

    gc = galaxy_client("partner_engineer")
    cnamespace = create_test_namespace(gc)
    collection = build_collection(namespace=cnamespace)
    ansible_galaxy(
        f"collection publish {collection.filename}",
        ansible_config=ansible_config("admin")
    )
    p = ansible_galaxy(
        f"collection publish {collection.filename}",
        check_retcode=1,
        ansible_config=ansible_config("admin")
    )
    assert "already exists" in str(p.stderr)


@pytest.mark.all
@pytest.mark.cli
@pytest.mark.skip_in_gw
@pytest.mark.usefixtures("cleanup_collections")
def test_publish_and_install_by_self(galaxy_client, published):
    """A publishing user has the permission to install an uncertified version of their
    own collection.
    """

    ansible_galaxy(
        f"collection install {published.namespace}.{published.name}:{published.version}",
        galaxy_client=galaxy_client("basic_user"),
    )


@pytest.mark.all
@pytest.mark.cli
@pytest.mark.deployment_cloud
@pytest.mark.skip_in_gw
@pytest.mark.usefixtures("cleanup_collections")
def test_publish_and_expect_uncertified_hidden(
    galaxy_client,
    published,
    settings,
    skip_if_require_signature_for_approval
):
    """A discovering/consumer user has the permission to download a specific version of an
    uncertified collection, but not an unspecified version range.
    """
    ansible_galaxy(
        f"collection install {published.namespace}.{published.name}",
        check_retcode=0,
        galaxy_client=galaxy_client("basic_user"),
    )
    ansible_galaxy(
        f"collection install {published.namespace}.{published.name}:1.0.0",
        galaxy_client=galaxy_client("basic_user"),
    )
