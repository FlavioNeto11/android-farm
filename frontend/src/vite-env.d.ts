declare module '*.module.css' {
  const classes: Record<string, string>;
  export default classes;
}

declare module '*.css' {
  const src: string;
  export default src;
}

interface ImportMetaEnv {
  readonly VITE_ANDROID_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
