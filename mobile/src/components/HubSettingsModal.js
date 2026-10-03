import React, { useState } from 'react';
import {
  Modal,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { NeoColors } from '../theme/neomorphism';

export default function HubSettingsModal({
  visible,
  currentUrl,
  onSave,
  onClose,
}) {
  const [inputUrl, setInputUrl] = useState(currentUrl);

  const presets = [
    { label: 'PC Wi-Fi (192.168.31.210)', url: 'http://192.168.31.210:8765' },
    { label: 'Localhost (8765)', url: 'http://localhost:8765' },
    { label: 'Emulator (10.0.2.2)', url: 'http://10.0.2.2:8765' },
  ];

  return (
    <Modal visible={visible} transparent animationType="slide">
      <View style={styles.overlay}>
        <View style={styles.content}>
          <Text style={styles.title}>⚙️ Hub Connection Settings</Text>
          <Text style={styles.desc}>
            Enter your computer's IP address on your local Wi-Fi:
          </Text>

          <TextInput
            style={styles.input}
            value={inputUrl}
            onChangeText={setInputUrl}
            placeholder="http://192.168.31.210:8765"
            placeholderTextColor="#94a3b8"
            autoCapitalize="none"
            autoCorrect={false}
          />

          <View style={styles.presetsSection}>
            <Text style={styles.presetsLabel}>Quick Presets:</Text>
            <View style={styles.presetsRow}>
              {presets.map((p, idx) => (
                <TouchableOpacity
                  key={idx}
                  style={styles.presetChip}
                  onPress={() => setInputUrl(p.url)}
                >
                  <Text style={styles.presetChipText}>{p.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          <View style={styles.btnRow}>
            <TouchableOpacity onPress={onClose} style={styles.cancelBtn}>
              <Text style={styles.cancelBtnText}>Cancel</Text>
            </TouchableOpacity>

            <TouchableOpacity
              onPress={() => onSave(inputUrl)}
              style={styles.saveBtn}
            >
              <Text style={styles.saveBtnText}>Save & Connect</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.65)',
    justifyContent: 'center',
    padding: 20,
  },
  content: {
    backgroundColor: '#ebf1f8',
    borderRadius: 18,
    padding: 20,
    borderWidth: 1,
    borderTopColor: '#ffffff',
    borderLeftColor: '#ffffff',
    borderBottomColor: '#c5d2e3',
    borderRightColor: '#c5d2e3',
    elevation: 6,
  },
  title: {
    fontSize: 17,
    fontWeight: '800',
    color: NeoColors.textPrimary,
    marginBottom: 6,
  },
  desc: {
    fontSize: 12,
    color: NeoColors.textSecondary,
    marginBottom: 12,
    lineHeight: 16,
  },
  input: {
    backgroundColor: '#ffffff',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: '#1e293b',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    marginBottom: 14,
  },
  presetsSection: {
    marginBottom: 16,
  },
  presetsLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: NeoColors.textMuted,
    marginBottom: 6,
  },
  presetsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  presetChip: {
    backgroundColor: '#ffffff',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#cbd5e1',
  },
  presetChipText: {
    fontSize: 11,
    color: '#2563eb',
    fontWeight: '600',
  },
  btnRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 10,
  },
  cancelBtn: {
    paddingVertical: 9,
    paddingHorizontal: 14,
    borderRadius: 8,
    backgroundColor: '#e2e8f0',
  },
  cancelBtnText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#475569',
  },
  saveBtn: {
    paddingVertical: 9,
    paddingHorizontal: 16,
    borderRadius: 8,
    backgroundColor: '#4f46e5',
  },
  saveBtnText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#ffffff',
  },
});
