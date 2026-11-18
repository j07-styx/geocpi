import React from "react";
import { createRoot } from "react-dom/client";
import PrototypeApp from "./PrototypeApp";
import "./prototype.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode><PrototypeApp /></React.StrictMode>
);
