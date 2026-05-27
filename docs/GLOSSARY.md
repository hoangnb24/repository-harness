# Glossary

## Agent

An AI coding collaborator operating inside the repository.

## Harness

The repo-level operating system that tells humans and agents how to turn intent
into safe product changes.

## Product Contract

The current expected behavior of the product. Product docs plus executable tests
become the living contract once implementation exists.

## Story Packet

A story-sized work file or folder that describes the product contract, affected
docs, design notes, and validation expectations for a feature.

## Feature Intake

The classification step that turns a prompt into tiny, normal, or high-risk
work before implementation begins.

## Component Taxonomy

A map from Harness files and capabilities to the responsibilities they serve,
used to evaluate coverage, attribute failures, and identify missing harness
capabilities.

## Maturity Level

A verifiable stage in Harness capability, from H0 bare environment through H5
self-improving harness. Each level has required files, criteria, and benchmark
indicators.

## Trace Quality Tier

The expected depth of a task trace: minimal for tiny work, standard for normal
work, and detailed for high-risk work.

## Context Phase

A phase of an agent task that changes what context should be read, such as
intake, planning, implementation, validation, or trace recording.

## Retrieval Trigger

A condition that tells an agent to fetch additional context, such as touching a
database schema, changing a public contract, or discovering missing validation.

## Harness Delta

A documentation, template, validation, backlog, or decision update that makes
future agent work safer or easier.

## Durable Layer

The SQLite database and CLI (`scripts/harness`) that stores operational records
(intakes, stories, decisions, backlog items, traces) as structured, queryable
data. Policy docs describe how to work; the durable layer stores what happened.

## Product Delta

A product-facing change such as code, tests, API shape, data model, or product
documentation.

## Trace

A structured record of what an agent did during a task: actions taken, files
read, files changed, decisions made, errors encountered, outcome, and any
harness friction discovered.
