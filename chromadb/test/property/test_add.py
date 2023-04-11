import pytest
from hypothesis import given, settings
import hypothesis.strategies as st
import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.test.configurations import configurations
import chromadb.test.property.strategies as strategies
import chromadb.test.property.invariants as invariants


@pytest.fixture(scope="module", params=configurations())
def api(request):
    configuration = request.param
    return chromadb.Client(configuration)


@given(collection=strategies.collections(), embeddings=strategies.embeddings())
def test_add(api, collection, embeddings):

    api.reset()

    coll = api.create_collection(**collection)
    coll.add(**embeddings)

    invariants.count(api, coll.name, len(collection))
    invariants.ann_accuracy(api, coll.name, embeddings)