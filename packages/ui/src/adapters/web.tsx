import React from "react";

export type BoxProps = {
  children?: React.ReactNode;
  flexDirection?: "row" | "column";
  padding?: number;
  paddingX?: number;
  paddingY?: number;
  marginTop?: number;
  marginBottom?: number;
  borderStyle?: "single" | "double" | "round";
  borderColor?: string;
  testId?: string;
  className?: string;
};

export type TextProps = {
  children?: React.ReactNode;
  bold?: boolean;
  dimColor?: boolean;
  color?: string;
  backgroundColor?: string;
  testId?: string;
  className?: string;
};

const CH = 8;

function boxStyle(props: BoxProps): React.CSSProperties {
  const style: React.CSSProperties = {
    display: "flex",
    flexDirection: props.flexDirection ?? "row",
    fontFamily: "ui-monospace, 'JetBrains Mono', 'Fira Mono', monospace",
    boxSizing: "border-box",
  };
  if (props.padding !== undefined) style.padding = props.padding * CH;
  if (props.paddingX !== undefined) {
    style.paddingLeft = props.paddingX * CH;
    style.paddingRight = props.paddingX * CH;
  }
  if (props.paddingY !== undefined) {
    style.paddingTop = props.paddingY * CH;
    style.paddingBottom = props.paddingY * CH;
  }
  if (props.marginTop !== undefined) style.marginTop = props.marginTop * CH;
  if (props.marginBottom !== undefined) style.marginBottom = props.marginBottom * CH;
  if (props.borderStyle) {
    style.border = `1px solid ${props.borderColor ?? "#414868"}`;
  }
  return style;
}

export function Box(props: BoxProps): React.ReactElement {
  return (
    <div
      style={boxStyle(props)}
      className={props.className}
      data-testid={props.testId}
    >
      {props.children}
    </div>
  );
}

function textStyle(props: TextProps): React.CSSProperties {
  const style: React.CSSProperties = {
    fontFamily: "ui-monospace, 'JetBrains Mono', 'Fira Mono', monospace",
    whiteSpace: "pre",
  };
  if (props.bold) style.fontWeight = 700;
  if (props.dimColor) style.opacity = 0.55;
  if (props.color) style.color = props.color;
  if (props.backgroundColor) style.backgroundColor = props.backgroundColor;
  return style;
}

export function Text(props: TextProps): React.ReactElement {
  return (
    <span
      style={textStyle(props)}
      className={props.className}
      data-testid={props.testId}
    >
      {props.children}
    </span>
  );
}

export type ListItemProps = {
  children?: React.ReactNode;
  testId?: string;
  className?: string;
};

export function ListItem(props: ListItemProps): React.ReactElement {
  return (
    <li
      className={props.className}
      data-testid={props.testId}
      style={{
        listStyle: "none",
        fontFamily: "ui-monospace, 'JetBrains Mono', 'Fira Mono', monospace",
        whiteSpace: "pre",
      }}
    >
      {props.children}
    </li>
  );
}
