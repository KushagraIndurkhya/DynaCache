import pickle
import binascii

def serialize_to_ascii(data):
    serialized_data = pickle.dumps(data)
    ascii_str = binascii.hexlify(serialized_data).decode("utf-8")
    return ascii_str

def deserialize_from_ascii(ascii_str):
    binary_data = binascii.unhexlify(ascii_str.encode("utf-8"))
    deserialized_data = pickle.loads(binary_data)
    return deserialized_data
