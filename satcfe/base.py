# -*- coding: utf-8 -*-
#
# satcfe/base.py
#
# Copyright 2015 Base4 Sistemas Ltda ME
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import ctypes
import os
import random

from ctypes import c_int
from ctypes import c_char_p

from satcomum import constantes

from .config import conf



class _Prototype(object):
    def __init__(self, argtypes, restype=c_char_p):
        self.argtypes = argtypes
        self.restype = restype


FUNCTION_PROTOTYPES = dict(
        AtivarSAT=_Prototype([c_int, c_int, c_char_p, c_char_p, c_int]),
        ComunicarCertificadoICPBRASIL=_Prototype([c_int, c_char_p, c_char_p]),
        EnviarDadosVenda=_Prototype([c_int, c_char_p, c_char_p]),
        CancelarUltimaVenda=_Prototype([c_int, c_char_p, c_char_p, c_char_p]),
        ConsultarSAT=_Prototype([c_int,]),
        TesteFimAFim=_Prototype([c_int, c_char_p, c_char_p]),
        ConsultarStatusOperacional=_Prototype([c_int, c_char_p]),
        ConsultarNumeroSessao=_Prototype([c_int, c_char_p, c_int]),
        ConfigurarInterfaceDeRede=_Prototype([c_int, c_char_p, c_char_p]),
        AssociarAssinatura=_Prototype([c_int, c_char_p, c_char_p, c_char_p]),
        AtualizarSoftwareSAT=_Prototype([c_int, c_char_p]),
        ExtrairLogs=_Prototype([c_int, c_char_p]),
        BloquearSAT=_Prototype([c_int, c_char_p]),
        DesbloquearSAT=_Prototype([c_int, c_char_p]),
        TrocarCodigoDeAtivacao=_Prototype([c_int, c_char_p, c_int, c_char_p, c_char_p])
    )


class DLLSAT(object):
    """
    Configura a localização da DLL do equipamento SAT e mantém uma
    referência carregada para a ela, conforme a convenção de chamada.
    """

    def __init__(self, convencao=constantes.STANDARD_C, caminho=None):
        super(DLLSAT, self).__init__()
        self.convencao = convencao
        self.caminho = caminho
        self.loadlib()


    def loadlib(self):
        self._libsat = None
        if constantes.STANDARD_C == self.convencao:
            loader = ctypes.CDLL
        elif constantes.WINDOWS_STDCALL == self.convencao:
            loader = ctypes.WinDLL
        else:
            raise ValueError('Convencao de chamada desconhecida: %s' %
                    self.convencao)
        self._libsat = loader(self.caminho)


    @property
    def ref(self):
        return self._libsat


    @property
    def caminho(self):
        return self._caminho


    @caminho.setter
    def caminho(self, valor):
        if not os.path.exists(valor):
            raise ValueError('Biblioteca (DLL) SAT inexistente no '
                    'caminho: %s' % valor)
        self._caminho = valor


    @property
    def convencao(self):
        return self._convencao


    @convencao.setter
    def convencao(self, valor):
        if valor not in [v for v,s in constantes.CONVENCOES_CHAMADA]:
            raise ValueError('Convencao de chamada desconhecida: %s' % valor)
        self._convencao = valor


class NumeroSessaoMemoria(object):
    """
    Implementa um numerador de sessão simples, baseado em memória, não
    persistente, que irá gerar um número de sessão (seis dígitos) diferente
    entre os 100 últimos números de sessão gerados, conforme recomendação.
    """

    def __init__(self, tamanho=100):
        super(NumeroSessaoMemoria, self).__init__()
        self._memoria = []
        self._tamanho = tamanho


    def __call__(self, *args, **kwargs):
        while True:
            numero = random.randint(100000, 999999)
            if numero not in self._memoria:
                self._memoria.append(numero)
                if len(self._memoria) > self._tamanho:
                    self._memoria.pop(0) # remove o mais antigo
                break
        return numero


class _FuncoesSAT(object):


    def __init__(self, dll=None, numerador_sessao=None):
        super(_FuncoesSAT, self).__init__()
        self._dll = dll
        self._numerador_sessao = numerador_sessao or NumeroSessaoMemoria()


    def gerar_numero_sessao(self):
        return self._numerador_sessao()


    def __getattr__(self, name):
        if name.startswith('invocar__'):
            metodo_sat = name.replace('invocar__', '')
            proto = FUNCTION_PROTOTYPES[metodo_sat]
            fptr = getattr(self._dll.ref, metodo_sat)
            fptr.argtypes = proto.argtypes
            fptr.restype = proto.restype
            return fptr
        raise AttributeError('\'%s\' object has no attribute \'%s\'' % (
                self.__class__.__name__, name,))


    def enviar_dados_venda(self, dados_venda):
        """
        ER SAT, item 6.1.3. Envia o CF-e de venda para o equipamento SAT, que o
        completará e o enviará para autorização pela SEFAZ.
        """
        numero_sessao = self.gerar_numero_sessao()
        codigo_ativacao = conf.codigo_ativacao
        return self.invocar__EnviarDadosVenda(
                numero_sessao, codigo_ativacao, dados_venda.xml)


    def consultar_sat(self):
        """
        ER SAT, item 6.1.5. Usada para testes de comunicação entre a AC e o
        equipamento SAT.
        """
        return self.invocar__ConsultarSAT(self.gerar_numero_sessao())


    def extrair_logs(self):
        """
        ER SAT, item 6.1.12. Extração dos registro de log do equipamento SAT.
        """
        return self.invocar__ExtrairLogs(
                self.gerar_numero_sessao(), conf.codigo_ativacao)