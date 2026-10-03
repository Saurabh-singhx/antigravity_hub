import React from 'react';
import { TouchableOpacity, Text, StyleSheet } from 'react-native';
import { NeoColors, NeoStyles } from '../theme/neomorphism';

export default function NeoButton({
  title,
  onPress,
  style,
  textStyle,
  variant = 'default', // 'default', 'primary', 'success', 'danger'
  disabled = false,
  children,
}) {
  const getVariantStyles = () => {
    switch (variant) {
      case 'primary':
        return { backgroundColor: '#4f46e5', textColor: '#ffffff' };
      case 'success':
        return { backgroundColor: '#10b981', textColor: '#ffffff' };
      case 'danger':
        return { backgroundColor: '#ef4444', textColor: '#ffffff' };
      default:
        return { backgroundColor: NeoColors.surface, textColor: NeoColors.textPrimary };
    }
  };

  const v = getVariantStyles();

  return (
    <TouchableOpacity
      activeOpacity={0.8}
      disabled={disabled}
      onPress={onPress}
      style={[
        NeoStyles.button,
        styles.base,
        { backgroundColor: v.backgroundColor },
        disabled && styles.disabled,
        style,
      ]}
    >
      {children || (
        <Text style={[styles.text, { color: v.textColor }, textStyle]}>
          {title}
        </Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
  text: {
    fontSize: 13,
    fontWeight: '700',
  },
  disabled: {
    opacity: 0.5,
  },
});
