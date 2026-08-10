import pytest
from das_llm.seeding import SimulationSeeder


def test_simulation_seeder_reproducibility():
    seed = 12345
    seeder1 = SimulationSeeder(seed=seed)
    seeder2 = SimulationSeeder(seed=seed)

    sequence1 = [seeder1.get_payload() for _ in range(20)]
    sequence2 = [seeder2.get_payload() for _ in range(20)]

    assert sequence1 == sequence2, "Two seeders initialized with the same integer must produce identical sequences."


def test_simulation_seeder_different_seeds():
    seeder1 = SimulationSeeder(seed=100)
    seeder2 = SimulationSeeder(seed=200)

    seq1 = [seeder1.get_payload() for _ in range(20)]
    seq2 = [seeder2.get_payload() for _ in range(20)]

    assert seq1 != seq2, "Seeders with different seeds should produce different payload sequences."


def test_simulation_seeder_custom_payloads():
    custom_payloads = ["payload_A", "payload_B"]
    seeder = SimulationSeeder(seed=42, payloads=custom_payloads)
    p = seeder.get_payload()
    assert p in custom_payloads
