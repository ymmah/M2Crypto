#!/usr/bin/env python
from __future__ import absolute_import, division

"""
Unit tests for M2Crypto.EVP.

Copyright (c) 2004-2007 Open Source Applications Foundation
Author: Heikki Toivonen
"""

import codecs
import hashlib
import io
import logging

from M2Crypto import BIO, EVP, RSA, Rand, m2, six, util

from binascii import a2b_hex, hexlify, unhexlify
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from tests.fips import fips_mode

log = logging.getLogger('test_EVP')


class EVPTestCase(unittest.TestCase):
    def _gen_callback(self, *args):
        pass

    def _pass_callback(self, *args):
        return 'foobar'

    def _assign_rsa(self):
        rsa = RSA.gen_key(1024, 3, callback=self._gen_callback)
        pkey = EVP.PKey()
        pkey.assign_rsa(rsa, capture=0)  # capture=1 should cause crash
        return rsa

    def test_assign(self):
        rsa = self._assign_rsa()
        rsa.check_key()

    @unittest.skipIf(six.PY3,
                     "test_pem hangs under python3 and is not yet fixed")
    def test_pem(self):
        rsa = RSA.gen_key(1024, 3, callback=self._gen_callback)
        pkey = EVP.PKey()
        pkey.assign_rsa(rsa)
        self.assertNotEqual(pkey.as_pem(callback=self._pass_callback),
                            pkey.as_pem(cipher=None))
        with self.assertRaises(ValueError):
            pkey.as_pem(cipher='noXX$$%%suchcipher',
                        callback=self._pass_callback)

    def test_as_der(self):
        """
        Test DER encoding the PKey instance after assigning
        a RSA key to it.
        """
        rsa = RSA.gen_key(1024, 3, callback=self._gen_callback)
        pkey = EVP.PKey()
        pkey.assign_rsa(rsa)
        der_blob = pkey.as_der()
        # A quick but not thorough sanity check
        self.assertEqual(len(der_blob), 160)

    def test_get_digestbyname(self):
        with self.assertRaises(EVP.EVPError):
            m2.get_digestbyname('sha513')
        self.assertNotEqual(m2.get_digestbyname('sha1'), None)

    def test_MessageDigest(self):  # noqa
        with self.assertRaises(ValueError):
            EVP.MessageDigest('sha513')
        md = EVP.MessageDigest('sha1')
        self.assertEqual(md.update(b'Hello'), 1)
        self.assertEqual(util.octx_to_num(md.final()),
                         1415821221623963719413415453263690387336440359920)

        # temporarily remove sha1 from m2
        old_sha1 = m2.sha1
        del m2.sha1

        # now run the same test again, relying on EVP.MessageDigest() to call
        # get_digestbyname() under the hood
        md = EVP.MessageDigest('sha1')
        self.assertEqual(md.update(b'Hello'), 1)
        self.assertEqual(util.octx_to_num(md.final()),
                         1415821221623963719413415453263690387336440359920)

        # put sha1 back in place
        m2.sha1 = old_sha1

    def test_as_der_capture_key(self):
        """
        Test DER encoding the PKey instance after assigning
        a RSA key to it. Have the PKey instance capture the RSA key.
        """
        rsa = RSA.gen_key(1024, 3, callback=self._gen_callback)
        pkey = EVP.PKey()
        pkey.assign_rsa(rsa, 1)
        der_blob = pkey.as_der()
        # A quick but not thorough sanity check
        self.assertEqual(len(der_blob), 160)

    def test_size(self):
        rsa = RSA.gen_key(1024, 3, callback=self._gen_callback)
        pkey = EVP.PKey()
        pkey.assign_rsa(rsa)
        size = pkey.size()
        self.assertEqual(size, 128)

    def test_hmac(self):
        self.assertEqual(util.octx_to_num(EVP.hmac(b'key', b'data')),
                         92800611269186718152770431077867383126636491933,
                         util.octx_to_num(EVP.hmac(b'key', b'data')))
        if not fips_mode:  # Disabled algorithms
            self.assertEqual(util.octx_to_num(EVP.hmac(b'key', b'data',
                                              algo='md5')),
                             209168838103121722341657216703105225176,
                             util.octx_to_num(EVP.hmac(b'key', b'data',
                                              algo='md5')))
            self.assertEqual(util.octx_to_num(EVP.hmac(b'key', b'data',
                                              algo='ripemd160')),
                             1176807136224664126629105846386432860355826868536,
                             util.octx_to_num(EVP.hmac(b'key', b'data',
                                              algo='ripemd160')))

        if m2.OPENSSL_VERSION_NUMBER >= 0x90800F:
            self.assertEqual(util.octx_to_num(EVP.hmac(b'key', b'data',
                                              algo='sha224')),
                             2660082265842109788381286338540662430962855478412025487066970872635,
                             util.octx_to_num(EVP.hmac(b'key', b'data',
                                              algo='sha224')))
            self.assertEqual(util.octx_to_num(EVP.hmac(b'key', b'data',
                                              algo='sha256')),
                             36273358097036101702192658888336808701031275731906771612800928188662823394256,
                             util.octx_to_num(EVP.hmac(b'key', b'data',
                                              algo='sha256')))
            self.assertEqual(util.octx_to_num(EVP.hmac(b'key', b'data',
                                              algo='sha384')),
                             30471069101236165765942696708481556386452105164815350204559050657318908408184002707969468421951222432574647369766282,
                             util.octx_to_num(EVP.hmac(b'key', b'data',
                                              algo='sha384')))
            self.assertEqual(util.octx_to_num(EVP.hmac(b'key', b'data',
                                              algo='sha512')),
                             3160730054100700080556942280820129108466291087966635156623014063982211353635774277148932854680195471287740489442390820077884317620321797003323909388868696,
                             util.octx_to_num(EVP.hmac(b'key', b'data',
                                              algo='sha512')))

        with self.assertRaises(ValueError):
            EVP.hmac(b'key', b'data', algo='sha513')

    @unittest.skipIf(six.PY3,
                     "test_get_rsa hangs under python3 and is not yet fixed")
    def test_get_rsa(self):
        """
        Testing retrieving the RSA key from the PKey instance.
        """
        rsa = RSA.gen_key(1024, 3, callback=self._gen_callback)
        self.assertIsInstance(rsa, RSA.RSA)
        pkey = EVP.PKey()
        pkey.assign_rsa(rsa)
        rsa2 = pkey.get_rsa()
        self.assertIsInstance(rsa2, RSA.RSA_pub)
        self.assertEqual(rsa.e, rsa2.e)
        self.assertEqual(rsa.n, rsa2.n)
        # FIXME
        # hanging call is
        #     m2.rsa_write_key(self.rsa, bio._ptr(), ciph, callback)s
        # from RSA.py/save_key_bio

        pem = rsa.as_pem(callback=self._pass_callback)
        pem2 = rsa2.as_pem()
        assert pem
        assert pem2
        self.assertNotEqual(pem, pem2)

        message = b'This is the message string'
        digest = hashlib.sha1(message).digest()
        self.assertEqual(rsa.sign(digest), rsa2.sign(digest))

        rsa3 = RSA.gen_key(1024, 3, callback=self._gen_callback)
        self.assertNotEqual(rsa.sign(digest), rsa3.sign(digest))

    @unittest.skipIf(six.PY3,
                     'FIXME test_load_key_string_pubkey hangs under python3')
    def test_load_key_string_pubkey(self):
        """
        Testing creating a PKey instance from PEM string.
        """
        rsa = RSA.gen_key(1024, 3, callback=self._gen_callback)
        self.assertIsInstance(rsa, RSA.RSA)

        rsa_pem = BIO.MemoryBuffer()
        rsa.save_pub_key_bio(rsa_pem)
        pkey = EVP.load_key_string_pubkey(rsa_pem.read())
        rsa2 = pkey.get_rsa()
        self.assertIsInstance(rsa2, RSA.RSA_pub)
        self.assertEqual(rsa.e, rsa2.e)
        self.assertEqual(rsa.n, rsa2.n)
        pem = rsa.as_pem(callback=self._pass_callback)
        pem2 = rsa2.as_pem()
        assert pem
        assert pem2
        self.assertNotEqual(pem, pem2)

    def test_get_rsa_fail(self):
        """
        Testing trying to retrieve the RSA key from the PKey instance
        when it is not holding a RSA Key. Should raise a ValueError.
        """
        pkey = EVP.PKey()
        with self.assertRaises(ValueError):
            pkey.get_rsa()

    def test_get_modulus(self):
        pkey = EVP.PKey()
        with self.assertRaises(ValueError):
            pkey.get_modulus()

        rsa = RSA.gen_key(1024, 3, callback=self._gen_callback)
        pkey.assign_rsa(rsa)
        mod = pkey.get_modulus()
        self.assertGreater(len(mod), 0, mod)
        self.assertEqual(len(mod.strip(b'0123456789ABCDEF')), 0)

    def test_verify_final(self):
        from M2Crypto import X509
        pkey = EVP.load_key('tests/signer_key.pem')
        pkey.sign_init()
        pkey.sign_update(b'test  message')
        sig = pkey.sign_final()

        # OK
        x509 = X509.load_cert('tests/signer.pem')
        pubkey = x509.get_pubkey()
        pubkey.verify_init()
        pubkey.verify_update(b'test  message')
        self.assertEqual(pubkey.verify_final(sig), 1)

        # wrong cert
        x509 = X509.load_cert('tests/x509.pem')
        pubkey = x509.get_pubkey()
        pubkey.verify_init()
        pubkey.verify_update(b'test  message')
        self.assertEqual(pubkey.verify_final(sig), 0)

        # wrong message
        x509 = X509.load_cert('tests/signer.pem')
        pubkey = x509.get_pubkey()
        pubkey.verify_init()
        pubkey.verify_update(b'test  message not')
        self.assertEqual(pubkey.verify_final(sig), 0)

    def test_load_bad(self):
        with self.assertRaises(BIO.BIOError):
            EVP.load_key('thisdoesnotexist-dfgh56789')
        with self.assertRaises(EVP.EVPError):
            EVP.load_key('tests/signer.pem')  # not a key
        with self.assertRaises(EVP.EVPError):
            EVP.load_key_bio(BIO.MemoryBuffer(b'no a key'))

    def test_pad(self):
        self.assertEqual(util.pkcs5_pad('Hello World'),
                         'Hello World\x05\x05\x05\x05\x05')
        self.assertEqual(util.pkcs7_pad('Hello World', 15),
                         'Hello World\x04\x04\x04\x04')
        with self.assertRaises(ValueError):
            util.pkcs7_pad('Hello', 256)

    def test_pkey_verify_crash(self):
        SIGN_PRIVATE = EVP.load_key('tests/rsa.priv.pem')
        SIGN_PUBLIC = RSA.load_pub_key('tests/rsa.pub.pem')

        def sign(data):
            SIGN_PRIVATE.sign_init()
            SIGN_PRIVATE.sign_update(data)
            signed_data = SIGN_PRIVATE.sign_final()
            return codecs.encode(signed_data, 'base64')

        def verify(response):
            signature = codecs.decode(response['sign'], 'base64')
            data = response['data']
            verify_evp = EVP.PKey()
            # capture parameter on the following line is required by
            # the documentation
            verify_evp.assign_rsa(SIGN_PUBLIC, capture=False)
            verify_evp.verify_init()
            verify_evp.verify_update(data)
            # m2.verify_final(self.ctx, sign, self.pkey)
            fin_res = verify_evp.verify_final(signature)
            return fin_res == 1

        data = b"test message"
        signature = sign(data)
        res = {"data": data, "sign": signature}
        self.assertTrue(verify(res))  # works fine
        self.assertTrue(verify(res))  # segmentation fault in *verify_final*

class CipherTestCase(unittest.TestCase):
    def cipher_filter(self, cipher, inf, outf):
        while 1:
            buf = inf.read()
            if not buf:
                break
            outf.write(cipher.update(buf))
        outf.write(cipher.final())
        return outf.getvalue()

    def try_algo(self, algo):
        enc = 1
        dec = 0
        otxt = b'against stupidity the gods themselves contend in vain'

        k = EVP.Cipher(algo, b'goethe', b'12345678', enc,
                       1, 'sha1', b'saltsalt', 5)
        pbuf = io.BytesIO(otxt)
        cbuf = io.BytesIO()
        ctxt = self.cipher_filter(k, pbuf, cbuf)
        pbuf.close()
        cbuf.close()

        j = EVP.Cipher(algo, b'goethe', b'12345678', dec,
                       1, 'sha1', b'saltsalt', 5)
        pbuf = io.BytesIO()
        cbuf = io.BytesIO(ctxt)
        ptxt = self.cipher_filter(j, cbuf, pbuf)
        pbuf.close()
        cbuf.close()

        self.assertEqual(otxt, ptxt, '%s algorithm cipher test failed' % algo)

    def test_ciphers(self):
        ciphers = [
            'des_ede_ecb', 'des_ede_cbc', 'des_ede_cfb', 'des_ede_ofb',
            'des_ede3_ecb', 'des_ede3_cbc', 'des_ede3_cfb', 'des_ede3_ofb',
            'aes_128_ecb', 'aes_128_cbc', 'aes_128_cfb', 'aes_128_ofb',
            'aes_128_ctr', 'aes_192_ecb', 'aes_192_cbc', 'aes_192_cfb',
            'aes_192_ofb', 'aes_192_ctr', 'aes_256_ecb', 'aes_256_cbc',
            'aes_256_cfb', 'aes_256_ofb', 'aes_256_ctr']
        nonfips_ciphers = ['bf_ecb', 'bf_cbc', 'bf_cfb', 'bf_ofb',
                           # 'idea_ecb', 'idea_cbc', 'idea_cfb', 'idea_ofb',
                           'cast5_ecb', 'cast5_cbc', 'cast5_cfb', 'cast5_ofb',
                           # 'rc5_ecb', 'rc5_cbc', 'rc5_cfb', 'rc5_ofb',
                           'des_ecb', 'des_cbc', 'des_cfb', 'des_ofb',
                           'rc4', 'rc2_40_cbc']
        if not fips_mode:  # Disabled algorithms
            ciphers += nonfips_ciphers
        for i in ciphers:
            self.try_algo(i)

        # idea might not be compiled in
        ciphers = ['idea_ecb', 'idea_cbc', 'idea_cfb', 'idea_ofb']
        try:
            for i in ciphers:
                self.try_algo(i)
        except ValueError as e:
            if str(e) != "('unknown cipher', 'idea_ecb')":
                raise

        # rc5 might not be compiled in
        ciphers = ['rc5_ecb', 'rc5_cbc', 'rc5_cfb', 'rc5_ofb']
        try:
            for i in ciphers:
                self.try_algo(i)
        except ValueError as e:
            if str(e) != "('unknown cipher', 'rc5_ecb')":
                raise

        with self.assertRaises(ValueError):
            self.try_algo('nosuchalgo4567')

    def test_AES(self):  # noqa
        enc = 1
        dec = 0
        tests = [
            # test vectors from rfc 3602
            # Case #1: Encrypting 16 bytes (1 block) using AES-CBC with
            # 128-bit key
            {
                'KEY': '06a9214036b8a15b512e03d534120006',
                'IV': '3dafba429d9eb430b422da802c9fac41',
                'PT': b'Single block msg',
                'CT': b'e353779c1079aeb82708942dbe77181a',
            },

            # Case #2: Encrypting 32 bytes (2 blocks) using AES-CBC with
            # 128-bit key
            {
                'KEY': 'c286696d887c9aa0611bbb3e2025a45a',
                'IV': '562e17996d093d28ddb3ba695a2e6f58',
                'PT': unhexlify(b'000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f'),
                'CT': b'd296cd94c2cccf8a3a863028b5e1dc0a7586602d253cfff91b8266bea6d61ab1',
            },

            # Case #3: Encrypting 48 bytes (3 blocks) using AES-CBC with
            # 128-bit key
            {
                'KEY': '6c3ea0477630ce21a2ce334aa746c2cd',
                'IV': 'c782dc4c098c66cbd9cd27d825682c81',
                'PT': b'This is a 48-byte message (exactly 3 AES blocks)',
                'CT': b'd0a02b3836451753d493665d33f0e8862dea54cdb293abc7506939276772f8d5021c19216bad525c8579695d83ba2684',
            },
        ]

        # Test with padding
        for test in tests:
            # encrypt
            k = EVP.Cipher(alg='aes_128_cbc', key=unhexlify(test['KEY']),
                           iv=unhexlify(test['IV']), op=enc)
            pbuf = io.BytesIO(test['PT'])
            cbuf = io.BytesIO()
            ciphertext = hexlify(self.cipher_filter(k, pbuf, cbuf))
            cipherpadding = ciphertext[len(test['PT']) * 2:]
            # Remove the padding from the end
            ciphertext = ciphertext[:len(test['PT']) * 2]
            pbuf.close()
            cbuf.close()
            self.assertEqual(ciphertext, test['CT'])

            # decrypt
            j = EVP.Cipher(alg='aes_128_cbc', key=unhexlify(test['KEY']),
                           iv=unhexlify(test['IV']), op=dec)
            pbuf = io.BytesIO()
            cbuf = io.BytesIO(unhexlify(test['CT'] + cipherpadding))
            plaintext = self.cipher_filter(j, cbuf, pbuf)
            pbuf.close()
            cbuf.close()
            self.assertEqual(plaintext, test['PT'])

        # Test without padding
        for test in tests:
            # encrypt
            k = EVP.Cipher(alg='aes_128_cbc', key=unhexlify(test['KEY']),
                           iv=unhexlify(test['IV']), op=enc, padding=False)
            pbuf = io.BytesIO(test['PT'])
            cbuf = io.BytesIO()
            ciphertext = hexlify(self.cipher_filter(k, pbuf, cbuf))
            pbuf.close()
            cbuf.close()
            self.assertEqual(ciphertext, test['CT'])

            # decrypt
            j = EVP.Cipher(alg='aes_128_cbc', key=unhexlify(test['KEY']),
                           iv=unhexlify(test['IV']), op=dec, padding=False)
            pbuf = io.BytesIO()
            cbuf = io.BytesIO(unhexlify(test['CT']))
            plaintext = self.cipher_filter(j, cbuf, pbuf)
            pbuf.close()
            cbuf.close()
            self.assertEqual(plaintext, test['PT'])

    def test_AES_ctr(self):  # noqa
        # In CTR mode, encrypt and decrypt are actually the same
        # operation because you encrypt the nonce value, then use the
        # output of that to XOR the plaintext.  So we set operation=0,
        # even though this setting is ignored by OpenSSL.
        op = 0

        nonce = unhexlify('4a45a048a1e9f7c1bd17f2908222b964')  # CTR nonce value, 16 bytes
        key = unhexlify('8410ad66fe53a09addc0d041ae00bc6d70e8038ec17019f27e52eecd3846757e')
        plaintext_value = b'This is three blocks of text with unicode char \x03'

        ciphertext_values = {
           '128': unhexlify('6098fb2e49b3f7ed34f841f43f825d84cf4834021511594b931c85f04662544bdb4f38232e9d87fda6280ab1ef450e27'),  # noqa
           '192': unhexlify('2299b1c5363824cb92b5851dedc73f49f30b23fb23f288492e840c951ce703292a5c6de6fc7f0625c403648f8ca4a582'),  # noqa
           '256': unhexlify('713e34bcd2c59affc9185a716c3c6aef5c9bf7b9914337dd96e9d7436344bcb9c35175afb54adb78aab322829ce9cb4a'),  # noqa
        }

        for key_size in [128, 192, 256]:
            alg = 'aes_%s_ctr' % str(key_size)
            log.info('Testing cipher %s', alg)

            # Our key for this test is 256 bits in length (32 bytes).
            # We will trim it to the appopriate length for testing AES-128
            # and AES-192 as well (so 16 and 24 bytes, respectively).
            key_truncated = key[0:(key_size // 8)]

            # Test encrypt operations
            cipher = EVP.Cipher(alg=alg, key=key_truncated, iv=nonce, op=op)
            ciphertext = cipher.update(plaintext_value)
            ciphertext = ciphertext + cipher.final()
            self.assertEqual(ciphertext, ciphertext_values[str(key_size)])

            # Test decrypt operations
            cipher = EVP.Cipher(alg=alg, key=key_truncated, iv=nonce, op=op)
            plaintext = cipher.update(ciphertext_values[str(key_size)])
            plaintext = plaintext + cipher.final()
            # XXX not quite sure this is the actual intention
            # but for now let's be happy to find the same content even if with
            # a different type - XXX
            self.assertEqual(plaintext, plaintext_value)

    def test_raises(self):
        def _cipherFilter(cipher, inf, outf):  # noqa
            while 1:
                buf = inf.read()
                if not buf:
                    break
                outf.write(cipher.update(buf))
            outf.write(cipher.final())
            return outf.getvalue()

        def decrypt(ciphertext, key, iv, alg='aes_256_cbc'):
            cipher = EVP.Cipher(alg=alg, key=key, iv=iv, op=0)
            pbuf = io.BytesIO()
            cbuf = io.BytesIO(ciphertext)
            plaintext = _cipherFilter(cipher, cbuf, pbuf)
            pbuf.close()
            cbuf.close()
            return plaintext

        with self.assertRaises(EVP.EVPError):
            decrypt(
                unhexlify('941d3647a642fab26d9f99a195098b91252c652d07235b9db35758c401627711724637648e45cad0f1121751a1240a4134998cfdf3c4a95c72de2a2444de3f9e40d881d7f205630b0d8ce142fdaebd8d7fbab2aea3dc47f5f29a0e9b55aae59222671d8e2877e1fb5cd8ef1c427027e0'),
                unhexlify('5f2cc54067f779f74d3cf1f78c735aec404c8c3a4aaaa02eb1946f595ea4cddb'),
                unhexlify('0001efa4bd154ee415b9413a421cedf04359fff945a30e7c115465b1c780a85b65c0e45c'))

        with self.assertRaises(EVP.EVPError):
            decrypt(
                unhexlify('a78a510416c1a6f1b48077cc9eeb4287dcf8c5d3179ef80136c18876d774570d'),
                unhexlify('5cd148eeaf680d4ff933aed83009cad4110162f53ef89fd44fad09611b0524d4'),
                unhexlify(''))


class PBKDF2TestCase(unittest.TestCase):
    def test_rfc3211_test_vectors(self):

        password = b'password'
        salt = unhexlify('1234567878563412')
        iter = 5
        keylen = 8
        ret = EVP.pbkdf2(password, salt, iter, keylen)
        self.assertEqual(ret, unhexlify(b'd1daa78615f287e6'))

        password = b'All n-entities must communicate with other n-entities' + \
            b' via n-1 entiteeheehees'
        salt = unhexlify('1234567878563412')
        iter = 500
        keylen = 16
        ret = EVP.pbkdf2(password, salt, iter, keylen)
        self.assertEqual(ret, unhexlify(b'6a8970bf68c92caea84a8df285108586'))


class HMACTestCase(unittest.TestCase):
    data1 = [b'', b'More text test vectors to stuff up EBCDIC machines :-)',
             a2b_hex("b760e92d6662d351eb3801057695ac0346295356")]

    data2 = [a2b_hex(b'0b' * 16), b"Hi There",
             a2b_hex("675b0b3a1b4ddf4e124872da6c2f632bfed957e9")]

    data3 = [b'Jefe', b"what do ya want for nothing?",
             a2b_hex("effcdf6ae5eb2fa2d27416d5f184df9c259a7c79")]

    data4 = [a2b_hex(b'aa' * 16), a2b_hex(b'dd' * 50),
             a2b_hex("d730594d167e35d5956fd8003d0db3d3f46dc7bb")]

    data = [data1, data2, data3, data4]

    def test_simple(self):
        algo = 'sha1'
        for d in self.data:
            h = EVP.HMAC(d[0], algo)
            h.update(d[1])
            ret = h.final()
            self.assertEqual(ret, d[2])
        with self.assertRaises(ValueError):
            EVP.HMAC(d[0], algo='nosuchalgo')

    def make_chain_HMAC(self, key, start, input, algo='sha1'):  # noqa
        chain = []
        hmac = EVP.HMAC(key, algo)
        hmac.update(repr(start))
        digest = hmac.final()
        chain.append((digest, start))
        for i in input:
            hmac.reset(digest)
            hmac.update(repr(i))
            digest = hmac.final()
            chain.append((digest, i))
        return chain

    def make_chain_hmac(self, key, start, input, algo='sha1'):
        chain = []
        digest = EVP.hmac(key, start, algo)
        chain.append((digest, start))
        for i in input:
            digest = EVP.hmac(digest, i, algo)
            chain.append((digest, i))
        return chain

    def verify_chain_hmac(self, key, start, chain, algo='sha1'):
        digest = EVP.hmac(key, start, algo)
        c = chain[0]
        if c[0] != digest or c[1] != start:
            return 0
        for d, v in chain[1:]:
            digest = EVP.hmac(digest, v, algo)
            if digest != d:
                return 0
        return 1

    def verify_chain_HMAC(self, key, start, chain, algo='sha1'):  # noqa
        hmac = EVP.HMAC(key, algo)
        hmac.update(start)
        digest = hmac.final()
        c = chain[0]
        if c[0] != digest or c[1] != start:
            return 0
        for d, v in chain[1:]:
            hmac.reset(digest)
            hmac.update(v)
            digest = hmac.final()
            if digest != d:
                return 0
        return 1

    def test_complicated(self):
        make_chain = self.make_chain_hmac
        verify_chain = self.verify_chain_hmac
        key = b'numero uno'
        start = b'zeroth item'
        input = [b'first item', b'go go go', b'fly fly fly']
        chain = make_chain(key, start, input)
        self.assertEqual(verify_chain(b'some key', start, chain), 0)
        self.assertEqual(verify_chain(key, start, chain), 1)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(EVPTestCase))
    suite.addTest(unittest.makeSuite(CipherTestCase))
    suite.addTest(unittest.makeSuite(PBKDF2TestCase))
    suite.addTest(unittest.makeSuite(HMACTestCase))
    return suite

if __name__ == '__main__':
    Rand.load_file('randpool.dat', -1)
    unittest.TextTestRunner().run(suite())
    Rand.save_file('randpool.dat')
