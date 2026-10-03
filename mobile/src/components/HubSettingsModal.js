import React, { useState, useEffect } from 'react';
import {
  Modal,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { NeoColors } from '../theme/neomorphism';

export default function HubSettingsModal({
  visible,
  currentUrl,
  currentToken = '',
  onSave,
  onClose,
}) {
  const [inputUrl, setInputUrl] = useState(currentUrl);
  const [inputToken, setInputToken] = useState(currentToken);
  const [showToken, setShowToken] = useState(false);
  const [testState, setTestState] = useState(null); // null | 'testing' | 'success' | 'auth_error' | 'net_error'
  const [testMessage, setTestMessage] = useState('');

  useEffect(() => {
    setInputUrl(currentUrl);
    setInputToken(currentToken);
    setTestState(null);
    setTestMessage('');
  }, [visible, currentUrl, currentToken]);

  const presets = [
    { label: 'PC Wi-Fi (192.168.31.210)', url: 'http://192.168.31.210:8765' },
    { label: 'Localhost (8765)', url: 'http://localhost:8765' },
    { label: 'Emulator (10.0.2.2)', url: 'http://10.0.2.2:8765' },
  ];

  const handleTestConnection = async () => {
    setTestState('testing');
    setTestMessage('Testing connection & credentials...');

    try {
      const cleanUrl = (inputUrl || '').trim().replace(/\/+$/, '');
      const headers = { 'Content-Type': 'application/json' };
      if (inputToken && inputToken.trim()) {
        headers['X-Hub-Token'] = inputToken.trim();
        headers['Authorization'] = `Bearer ${inputToken.trim()}`;
      }

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);

      const res = await fetch(`${cleanUrl}/api/auth/verify`, {
        method: 'GET',
        headers,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        setTestState('success');
        setTestMessage('✅ Verified! Backend reachable & authenticated.');
      } else if (res.status === 401) {
        setTestState('auth_error');
        setTestMessage('❌ 401 Unauthorized: Invalid or missing Hub Token.');
      } else {
        setTestState('auth_error');
        setTestMessage(`⚠️ Server responded with status ${res.status}.`);
      }
    } catch (e) {
      setTestState('net_error');
      setTestMessage(`❌ Unreachable: ${e.message || 'Check IP & Wi-Fi'}`);
    }
  };

  return (
    <Modal visible={visible} transparent animationType="slide">
      <View style={styles.overlay}>
        <View style={styles.content}>
          <Text style={styles.title}>⚙️ Hub Connection & Security</Text>
          <Text style={styles.desc}>
            Configure your PC relay endpoint and pre-shared Hub Token.
          </Text>

          {/* Hub URL Input */}
          <Text style={styles.inputLabel}>Hub Relay URL:</Text>
          <TextInput
            style={styles.input}
            value={inputUrl}
            onChangeText={(txt) => {
              setInputUrl(txt);
              setTestState(null);
            }}
            placeholder="http://192.168.31.210:8765"
            placeholderTextColor="#94a3b8"
            autoCapitalize="none"
            autoCorrect={false}
          />

          {/* Quick Presets */}
          <View style={styles.presetsSection}>
            <Text style={styles.presetsLabel}>Quick Presets:</Text>
            <View style={styles.presetsRow}>
              {presets.map((p, idx) => (
                <TouchableOpacity
                  key={idx}
                  style={styles.presetChip}
                  onPress={() => {
                    setInputUrl(p.url);
                    setTestState(null);
                  }}
                >
                  <Text style={styles.presetChipText}>{p.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          {/* Hub Token Input */}
          <View style={styles.tokenHeaderRow}>
            <Text style={styles.inputLabel}>Security Token (X-Hub-Token):</Text>
            <TouchableOpacity onPress={() => setShowToken(!showToken)}>
              <Text style={styles.toggleText}>{showToken ? '🙈 Hide' : '👁️ Show'}</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.tokenInputContainer}>
            <TextInput
              style={styles.tokenInput}
              value={inputToken}
              onChangeText={(txt) => {
                setInputToken(txt);
                setTestState(null);
              }}
              placeholder="Paste token from .hub_secret"
              placeholderTextColor="#94a3b8"
              secureTextEntry={!showToken}
              autoCapitalize="none"
              autoCorrect={false}
            />
            {inputToken ? (
              <TouchableOpacity
                onPress={() => {
                  setInputToken('');
                  setTestState(null);
                }}
                style={styles.clearBtn}
              >
                <Text style={styles.clearBtnText}>✕</Text>
              </TouchableOpacity>
            ) : null}
          </View>

          {/* Test Status Indicator */}
          {testMessage ? (
            <View
              style={[
                styles.testStatusBox,
                testState === 'success' && styles.testSuccess,
                (testState === 'auth_error' || testState === 'net_error') && styles.testError,
              ]}
            >
              {testState === 'testing' ? (
                <ActivityIndicator size="small" color="#4f46e5" style={{ marginRight: 6 }} />
              ) : null}
              <Text style={styles.testStatusText}>{testMessage}</Text>
            </View>
          ) : null}

          {/* Action Buttons */}
          <View style={styles.btnRow}>
            <TouchableOpacity
              onPress={handleTestConnection}
              style={styles.testBtn}
              disabled={testState === 'testing'}
            >
              <Text style={styles.testBtnText}>🔍 Test Auth</Text>
            </TouchableOpacity>

            <TouchableOpacity onPress={onClose} style={styles.cancelBtn}>
              <Text style={styles.cancelBtnText}>Cancel</Text>
            </TouchableOpacity>

            <TouchableOpacity
              onPress={() => onSave(inputUrl, inputToken)}
              style={styles.saveBtn}
            >
              <Text style={styles.saveBtnText}>Save</Text>
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
    marginBottom: 4,
  },
  desc: {
    fontSize: 12,
    color: NeoColors.textSecondary,
    marginBottom: 12,
    lineHeight: 16,
  },
  inputLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: NeoColors.textSecondary,
    marginBottom: 4,
  },
  tokenHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  toggleText: {
    fontSize: 11,
    color: '#4f46e5',
    fontWeight: '600',
  },
  input: {
    backgroundColor: '#ffffff',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 9,
    fontSize: 13,
    color: '#1e293b',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    marginBottom: 10,
  },
  tokenInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#cbd5e1',
    marginBottom: 12,
    paddingHorizontal: 12,
  },
  tokenInput: {
    flex: 1,
    paddingVertical: 9,
    fontSize: 13,
    color: '#1e293b',
  },
  clearBtn: {
    padding: 4,
  },
  clearBtnText: {
    color: '#94a3b8',
    fontSize: 14,
    fontWeight: '700',
  },
  presetsSection: {
    marginBottom: 12,
  },
  presetsLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: NeoColors.textMuted,
    marginBottom: 4,
  },
  presetsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  presetChip: {
    backgroundColor: '#ffffff',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#cbd5e1',
  },
  presetChipText: {
    fontSize: 10,
    color: '#2563eb',
    fontWeight: '600',
  },
  testStatusBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f1f5f9',
    padding: 8,
    borderRadius: 8,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#cbd5e1',
  },
  testSuccess: {
    backgroundColor: '#ecfdf5',
    borderColor: '#a7f3d0',
  },
  testError: {
    backgroundColor: '#fef2f2',
    borderColor: '#fecaca',
  },
  testStatusText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#1e293b',
    flex: 1,
  },
  btnRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: 8,
    marginTop: 4,
  },
  testBtn: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: '#e0e7ff',
    marginRight: 'auto',
  },
  testBtnText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#4338ca',
  },
  cancelBtn: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: '#e2e8f0',
  },
  cancelBtnText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#475569',
  },
  saveBtn: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
    backgroundColor: '#4f46e5',
  },
  saveBtnText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#ffffff',
  },
});
