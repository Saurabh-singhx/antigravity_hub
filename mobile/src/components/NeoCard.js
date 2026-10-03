import React from 'react';
import { View, StyleSheet } from 'react-native';
import { NeoColors, NeoStyles } from '../theme/neomorphism';

export default function NeoCard({ children, style, pressed = false }) {
  return (
    <View style={[pressed ? NeoStyles.inset : NeoStyles.card, styles.base, style]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    padding: 14,
    marginBottom: 12,
  },
});
