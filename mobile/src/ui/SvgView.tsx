// A picture from the server (an SVG string) drawn to fit the width of the screen.
import React, { useState } from "react";
import { View } from "react-native";
import { SvgXml } from "react-native-svg";
import { fitSvg } from "./svg";

export function SvgView({ xml, maxScale = 1 }: { xml: string; maxScale?: number }) {
  const [avail, setAvail] = useState(0);
  const size = fitSvg(xml, avail, maxScale);
  return (
    <View onLayout={(e: any) => setAvail(e.nativeEvent.layout.width)} style={{ width: "100%", backgroundColor: "#fff" }} accessibilityRole="image" accessibilityLabel="Written text">
      {size ? <SvgXml xml={xml} width={size.width} height={size.height} /> : null}
    </View>
  );
}
