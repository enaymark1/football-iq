import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { APP_NAME } from "./config";
import { MetaProvider } from "./hooks/useMeta";
import "./index.css";

document.title = APP_NAME;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <MetaProvider>
        <App />
      </MetaProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
