import * as React from 'react';
import { PageSection, Title } from '@patternfly/react-core';

const Dashboard: React.FunctionComponent = () => {
  return (
    <PageSection hasBodyWrapper={false}>
      <Title headingLevel="h1" size="lg">Dashboard Page Title!</Title>
      <div style={{ marginTop: '20px' }}>
        <p>Welcome to your dashboard! Use the navigation to explore different sections of the application.</p>
      </div>
    </PageSection>
  );
};

export { Dashboard };
