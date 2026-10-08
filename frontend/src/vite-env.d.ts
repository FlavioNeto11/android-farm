declare module '*.module.css' {
  const classes: Record<string, string>;
  export default classes;
}

declare module '*.css' {
  const src: string;
  export default src;
}
