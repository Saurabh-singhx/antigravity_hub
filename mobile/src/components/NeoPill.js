import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { NeoColors } from '../theme/neomorphism';

export default function NeoPill({ label, color, bgColor, icon, style, textStyle }) {
  const textColor = color || NeoColors.primary;
  const background = bgColor || `${textColor}15`;

  return (
    <View style={[styles.pill, { backgroundColor: background }, style]}>
      {icon ? <Text style={styles.icon}>{icon}</Text> : null}
      <Text style={[styles.text, { color: textColor }, textStyle]}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.6)',
  },
  icon: {
    fontSize: 10,
    marginRight: 4,
  },
  text: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
});
