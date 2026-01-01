import React from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';

const FeatureList = [
  {
    title: 'Database-Level Security',
    description: (
      <>
        Security enforced by PostgreSQL, not application code. No more forgetting
        to filter querysets - RLS ensures users only see data they're authorized to access.
      </>
    ),
  },
  {
    title: 'Django Integration',
    description: (
      <>
        Seamlessly integrates with Django's ORM, middleware, and admin. Works with
        existing models and requires minimal code changes. Following Django REST Framework patterns.
      </>
    ),
  },
  {
    title: 'Multi-Tenant Ready',
    description: (
      <>
        Built-in support for multi-tenant applications. Tenant isolation happens at
        the database level, ensuring complete data separation with optimal performance.
      </>
    ),
  },
  {
    title: 'Flexible Policies',
    description: (
      <>
        Create simple user-based policies or complex custom rules. Combine multiple
        policies for fine-grained access control. Supports all SQL operations.
      </>
    ),
  },
  {
    title: 'Developer Friendly',
    description: (
      <>
        Clear API following Django conventions. Comprehensive testing utilities.
        Detailed documentation with real-world examples. Easy debugging and monitoring.
      </>
    ),
  },
  {
    title: 'Production Ready',
    description: (
      <>
        Battle-tested security with field validation. Performance optimized with proper
        indexing support. Management commands for easy deployment and maintenance.
      </>
    ),
  },
];

function Feature({title, description}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center padding-horiz--md">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}