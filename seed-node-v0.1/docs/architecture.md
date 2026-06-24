# Architecture

## Doctrine

One Synnergyze Core. Many templates. Many deployment modes.

## Layers

1. Individual workspace
2. Creator workspace
3. Professional workspace
4. Business Lite
5. Genesis Business
6. Enterprise
7. Enterprise-to-enterprise network

## Database separation

The first VM uses one PostgreSQL server with separate schemas:

- platform
- workspace
- textile
- business
- genesis
- riveros
- silk

Later, business and enterprise tenants can be moved to separate databases or clusters.

## First module

Textile Workspace Builder:

Physical swatch → Material Passport → Virtual Design → BOM → Tech Pack → Payment Event → Evidence Log.
