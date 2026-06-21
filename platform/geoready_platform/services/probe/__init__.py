"""AI Perception Probe (Phase 1).

Pure layers (taxonomy, prompt_generator, share_of_model, hallucination) contain
no I/O and are fully unit-testable offline. The runner orchestrates them with
the engine bridge and persistence.
"""
