"""Semantic Layer REST API integration for Superset.

This package bundles three pieces that work together:

- :mod:`sl_db_engine_spec.adapter`   — a Shillelagh adapter that talks to a
                                       Semantic Layer REST API server.
- :mod:`sl_db_engine_spec.dialect`   — a SQLAlchemy dialect that exposes
                                       semantic views as SQL tables.
- :mod:`sl_db_engine_spec.engine_spec` — a Superset DB engine spec that
                                         renders the connection form,
                                         translates metrics, and handles
                                         OAuth2.

Each piece is wired up through the standard entry-point group for its host
project (``shillelagh.adapter``, ``sqlalchemy.dialects``,
``superset.db_engine_specs``), so installing this package is enough.
"""
