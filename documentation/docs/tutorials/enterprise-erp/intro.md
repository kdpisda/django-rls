---
sidebar_position: 1
---

# Introduction

Welcome to the **Enterprise ERP Tutorial**. In this multi-part series, we will build a comprehensive, secure ERP system for a fictional company called **MegaCorp**.

This tutorial goes beyond basic "Hello World" examples. We will implementation complex, real-world security requirements that you would encounter in a large-scale enterprise application.

## The Scenario: MegaCorp

MegaCorp is a large organization with strict data governance rules. They are building a new internal document management system and have the following security requirements:

### 1. Strict Departmental Isolation
*   **Requirement**: Data is strictly siloed by department.
*   **Example**: A "Sales" employee must never see "Engineering" documents by default.

### 2. Hierarchical Visibility (The "Manager" Rule)
*   **Requirement**: Managers must see data from their own department **AND** all sub-departments.
*   **Example**: The "VP of Engineering" can see documents from:
    *   Engineering (Their direct dept)
    *   Backend Team (Sub-dept)
    *   Frontend Team (Sub-dept)
    *   DevOps (Sub-dept)

### 3. Cross-Department Collaboration (ACLs)
*   **Requirement**: Occasional exceptions are needed for collaboration.
*   **Example**: Alice from Sales needs to view a specific Engineering specification. We need a way to grant her specific access without opening up the entire Engineering folder.

### 4. The "Auditor" Role (Dynamic Context)
*   **Requirement**: Compliance officers (Auditors) need read-only access to **everything**.
*   **Identifier**: Anyone logging in with an email ending in `@audit.megacorp.com`.

## Why Django RLS?

Implementing these rules in standard Django `views.py` is:
*   **Error-prone**: You have to remember to filter `Document.objects.filter(...)` in every single view, API endpoint, and admin page.
*   **Complex**: Hierarchical queries (get all children of children) are hard to express in standard ORM filters without inefficient Python loops or complex Q objects.
*   **Insecure**: One forgotten filter exposes confidential data.

**Django RLS** pushes this logic into the **PostgreSQL database** itself. No matter how you query the data (`.all()`, `.filter()`, distinct, union), the database ensures you only see what you are allowed to see.

## Prerequisites

*   Python 3.10+
*   Django 5.0+
*   PostgreSQL 12+
*   Basic understanding of Django Models

Let's get started by setting up our project structure.
