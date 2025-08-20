import React from "react";
import ReactDOM from "react-dom/client";
import App from '@app/index';

if (process.env.NODE_ENV !== "production") {
  const config = {
    rules: [
      {
        id: 'color-contrast',
        enabled: false
      }
    ]
  };
  import("react-axe").then(axe => {
    axe.default(React, ReactDOM, 1000, config);
  });
}

const root = ReactDOM.createRoot(document.getElementById("root") as Element);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
