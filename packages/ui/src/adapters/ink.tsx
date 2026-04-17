import React from "react";
import { Box as InkBox, Text as InkText } from "ink";

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

export function Box(props: BoxProps): React.ReactElement {
  const { testId: _t, className: _c, ...rest } = props;
  return <InkBox {...rest}>{props.children}</InkBox>;
}

export function Text(props: TextProps): React.ReactElement {
  const { testId: _t, className: _c, children, ...rest } = props;
  return <InkText {...rest}>{children}</InkText>;
}

export type ListItemProps = {
  children?: React.ReactNode;
  testId?: string;
  className?: string;
};

export function ListItem(props: ListItemProps): React.ReactElement {
  return (
    <InkBox>
      <InkText>{props.children}</InkText>
    </InkBox>
  );
}
