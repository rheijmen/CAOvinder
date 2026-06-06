from cao_engine.extraction.sectioned.mistral_sectioned import make_mistral_generate


def test_factory_returns_callable():
    generate = make_mistral_generate("dummy-key", "mistral-large-latest")
    assert callable(generate)
