// Stand-ins for react / react-native / expo so the app's own TypeScript can be checked without installing them.
// Everything from the libraries is `any`; the app's own functions, props and imports are still checked.
declare module "react" {
  namespace React { type ReactNode = any; }
  const React: any; export default React;
  export function useState<T>(i: T | (() => T)): [T, (v: T | ((p: T) => T)) => void];
  export function useEffect(f: () => void | (() => void), d?: any[]): void;
  export function useReducer(r: (s: number) => number, i: number): [number, () => void];
  export function useMemo<T>(f: () => T, d: any[]): T;
  export function useCallback<T>(f: T, d: any[]): T;
  export function useRef<T>(i: T): { current: T };
  export function useRef<T>(i: T | null): { current: T | null };
  export function createContext<T>(d: T): { __t: T; Provider: any };
  export function useContext<T>(c: { __t: T }): T;
  export type ReactNode = any;
}
declare module "react/jsx-runtime" { export const jsx: any, jsxs: any, Fragment: any; }
declare namespace JSX { interface IntrinsicAttributes { key?: any; ref?: any } type Element = any; interface IntrinsicElements { [k: string]: any } interface ElementChildrenAttribute { children: {} } }
declare module "react-native" {
  export const StatusBar: { currentHeight?: number };
  export const ActivityIndicator: any, Alert: any, BackHandler: any, KeyboardAvoidingView: any, Linking: any, Modal: any,
    Image: any, Platform: any, Pressable: any, RefreshControl: any, ScrollView: any, Share: any, StyleSheet: any, Text: any, TextInput: any, View: any, Switch: any;
  export type TextInputProps = any; export type ViewStyle = any;
  export function FlatList<T>(p: { data: T[]; renderItem: (i: { item: T; index: number }) => any; keyExtractor: (item: T, index: number) => string; [k: string]: any }): any;
  export function SectionList<T>(p: { sections: { title: string; data: T[] }[]; renderItem: (i: { item: T; index: number }) => any; keyExtractor: (item: T, index: number) => string; renderSectionHeader?: (i: { section: { title: string; data: T[] } }) => any; [k: string]: any }): any;
  export interface FlatList<T> { scrollToIndex(o: any): void; scrollToOffset(o: any): void }
  export interface SectionList<T> { scrollToLocation(o: any): void }
}
declare module "expo-secure-store" { export function getItemAsync(k: string): Promise<string | null>; export function setItemAsync(k: string, v: string): Promise<void>; export function deleteItemAsync(k: string): Promise<void>; }
declare module "expo-status-bar" { export const StatusBar: any; }
declare module "expo-crypto" { export const getRandomBytesAsync: any, digestStringAsync: any, CryptoDigestAlgorithm: any, CryptoEncoding: any; }
declare module "expo-linking" { export const createURL: any; }
declare module "expo-web-browser" { export const maybeCompleteAuthSession: any, openAuthSessionAsync: any; }
declare module "expo-file-system" { export class Directory { static pickDirectoryAsync(initialUri?: string): Promise<Directory>; createFile(name: string, mimeType: string | null): File } export class File { constructor(...a: any[]); exists: boolean; uri: string; create(...a: any[]): void; write(s: string): void; delete(): void } export const Paths: any; }
declare module "expo-sharing" { export const isAvailableAsync: any, shareAsync: any; }
declare function btoa(s: string): string;
declare module "react-native-svg" { export const SvgXml: any; }
declare module "react-native-view-shot" { const ViewShot: any; export default ViewShot; }
declare module "expo-image-picker" { export const launchImageLibraryAsync: (o: any) => Promise<{ canceled: boolean; assets?: { uri: string; width: number; height: number }[] }>; }
declare module "expo-image-manipulator" { export const manipulateAsync: (uri: string, actions: any[], o: any) => Promise<{ uri: string; width: number; height: number; base64?: string }>; export const SaveFormat: { JPEG: any; PNG: any }; }
declare module "jpeg-js" { export function decode(data: Uint8Array, o?: any): { width: number; height: number; data: Uint8Array }; }
